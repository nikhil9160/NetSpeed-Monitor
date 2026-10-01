import time
import psutil
from collections import deque

def get_network_interfaces():
    """Returns a list of active network interface names."""
    try:
        interfaces = ["All Interfaces"]
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        for iface, stat in stats.items():
            if stat.isup and iface in addrs:
                interfaces.append(iface)
        return interfaces
    except Exception as e:
        print(f"Error fetching network interfaces: {e}")
        return ["All Interfaces"]

def format_bytes_human(bytes_val):
    """Formats bytes into human-readable B, KB, MB, GB."""
    if bytes_val < 1024:
        return f"{bytes_val:.0f} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024.0:.1f} KB"
    elif bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / (1024.0 * 1024.0):.2f} MB"
    else:
        return f"{bytes_val / (1024.0 * 1024.0 * 1024.0):.2f} GB"

def format_speed(bytes_sec, mode="MB/s"):
    """
    Formats speed according to user preference mode without unexpected auto-switching:
    'MB/s' -> Strictly MegaBytes per second (e.g. 0.00 MB/s, 1.45 MB/s)
    'Mbps' -> Strictly Megabits per second (e.g. 0.00 Mbps, 11.60 Mbps)
    'KB/s' -> Strictly KiloBytes per second (e.g. 0.0 KB/s, 240.5 KB/s)
    'Auto' -> Dynamic auto-scaling (B/s, KB/s, MB/s, GB/s)
    """
    if bytes_sec < 0:
        bytes_sec = 0.0

    if mode == "Mbps":
        bits_sec = bytes_sec * 8.0
        mbps = bits_sec / (1000.0 * 1000.0)  # Standard Mbps (10^6 bits)
        if mbps >= 100:
            return f"{mbps:.1f} Mbps"
        else:
            return f"{mbps:.2f} Mbps"

    elif mode == "KB/s":
        kb_s = bytes_sec / 1024.0
        if kb_s >= 1000:
            return f"{kb_s:.0f} KB/s"
        else:
            return f"{kb_s:.1f} KB/s"

    elif mode == "MB/s":
        mb_s = bytes_sec / (1024.0 * 1024.0)
        if mb_s >= 100:
            return f"{mb_s:.1f} MB/s"
        else:
            return f"{mb_s:.2f} MB/s"

    else:  # Auto dynamic mode
        if bytes_sec < 1024:
            return f"{bytes_sec:.0f} B/s"
        elif bytes_sec < 1024 * 1024:
            return f"{bytes_sec / 1024.0:.1f} KB/s"
        elif bytes_sec < 1024 * 1024 * 1024:
            return f"{bytes_sec / (1024.0 * 1024.0):.2f} MB/s"
        else:
            return f"{bytes_sec / (1024.0 * 1024.0 * 1024.0):.2f} GB/s"

class NetworkTracker:
    def __init__(self, history_size=60):
        self.selected_interface = "All Interfaces"
        self.last_bytes_recv = 0
        self.last_bytes_sent = 0
        self.last_time = time.time()
        
        self.dl_speed = 0.0  # bytes/sec
        self.ul_speed = 0.0  # bytes/sec
        
        self.total_downloaded = 0  # bytes
        self.total_uploaded = 0    # bytes
        
        self.peak_dl_speed = 0.0
        self.peak_ul_speed = 0.0
        
        self.dl_history = deque(maxlen=history_size)
        self.ul_history = deque(maxlen=history_size)
        
        # Initialize initial baseline
        self.reset_counters()

    def set_interface(self, interface_name):
        self.selected_interface = interface_name
        self.reset_counters()

    def reset_counters(self):
        try:
            if self.selected_interface == "All Interfaces" or not self.selected_interface:
                counters = psutil.net_io_counters(pernic=False)
            else:
                pernic = psutil.net_io_counters(pernic=True)
                counters = pernic.get(self.selected_interface, psutil.net_io_counters(pernic=False))
            
            if counters:
                self.last_bytes_recv = counters.bytes_recv
                self.last_bytes_sent = counters.bytes_sent
            self.last_time = time.time()
        except Exception as e:
            print(f"Error resetting counters: {e}")

    def update(self):
        """Measures byte deltas and computes current download and upload speeds."""
        now = time.time()
        dt = now - self.last_time
        if dt <= 0:
            dt = 0.001

        try:
            if self.selected_interface == "All Interfaces" or not self.selected_interface:
                counters = psutil.net_io_counters(pernic=False)
            else:
                pernic = psutil.net_io_counters(pernic=True)
                counters = pernic.get(self.selected_interface, None)
                if not counters:
                    counters = psutil.net_io_counters(pernic=False)

            if counters:
                bytes_recv = counters.bytes_recv
                bytes_sent = counters.bytes_sent

                # Handle potential counter rollover or reset
                if bytes_recv >= self.last_bytes_recv:
                    delta_recv = bytes_recv - self.last_bytes_recv
                else:
                    delta_recv = 0

                if bytes_sent >= self.last_bytes_sent:
                    delta_sent = bytes_sent - self.last_bytes_sent
                else:
                    delta_sent = 0

                self.dl_speed = delta_recv / dt
                self.ul_speed = delta_sent / dt

                self.total_downloaded += delta_recv
                self.total_uploaded += delta_sent

                if self.dl_speed > self.peak_dl_speed:
                    self.peak_dl_speed = self.dl_speed
                if self.ul_speed > self.peak_ul_speed:
                    self.peak_ul_speed = self.ul_speed

                self.last_bytes_recv = bytes_recv
                self.last_bytes_sent = bytes_sent
            else:
                self.dl_speed = 0.0
                self.ul_speed = 0.0
        except Exception as e:
            print(f"Error updating network stats: {e}")
            self.dl_speed = 0.0
            self.ul_speed = 0.0

        self.last_time = now
        self.dl_history.append(self.dl_speed)
        self.ul_history.append(self.ul_speed)

        return self.dl_speed, self.ul_speed
