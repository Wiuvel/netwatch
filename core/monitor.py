# -*- coding: utf-8 -*-
import time
import logging
import psutil
import ipaddress
import threading
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger("NetWatch")

class ProcessMonitor(QObject):
    new_subnets_signal = pyqtSignal(set)
    conn_counts_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, process_name):
        super().__init__()
        self.process_name = process_name
        self.running = False
        self._thread = None
        self.seen_ips = set()

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _run(self):
        try:
            while self.running:
                current_subnets, conn_counts = self._collect_subnets()
                new_subnets = current_subnets - self.seen_ips
                if new_subnets:
                    self.seen_ips |= new_subnets
                    self.new_subnets_signal.emit(new_subnets)
                if conn_counts:
                    self.conn_counts_signal.emit(conn_counts)
                time.sleep(2)
        except Exception as e:
            logger.exception("Monitor thread error")
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()

    def _collect_subnets(self):
        subs = set()
        conn_counts = {}
        try:
            target_pids = set()
            for p in psutil.process_iter(['name']):
                try:
                    if p.info.get('name') and p.info['name'].lower() == self.process_name.lower():
                        target_pids.add(p.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not target_pids:
                return subs, conn_counts

            try:
                connections = psutil.net_connections(kind='inet')
            except psutil.AccessDenied:
                connections = []
                for pid in target_pids:
                    try:
                        p = psutil.Process(pid)
                        connections.extend(p.net_connections(kind='inet'))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            for c in connections:
                if c.pid in target_pids and c.raddr:
                    try:
                        ip = ipaddress.ip_address(c.raddr.ip)
                        if ip.is_loopback or ip.is_link_local or ip.is_multicast:
                            continue

                        if ip.version == 4:
                            network = ipaddress.ip_network(f"{ip}/32", strict=False)
                        else:
                            network = ipaddress.ip_network(f"{ip}/128", strict=False)
                        subs.add(network)
                        net_str = str(network)
                        conn_counts[net_str] = conn_counts.get(net_str, 0) + 1
                    except (ValueError, TypeError):
                        continue
        except Exception as e:
            logger.exception(f"Collect subnets failed: {e}")
        return subs, conn_counts
