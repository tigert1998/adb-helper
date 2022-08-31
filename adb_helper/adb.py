import os
import subprocess
import multiprocessing as mp
import csv
import datetime


class Adb:
    def __init__(self, adb_device_id: str, su: bool, adb_path="adb"):
        self.adb_device_id = adb_device_id
        self.su = su
        self.adb_path = adb_path

    def push(self, local_path: str, remote_path: str):
        assert 0 == os.system("{} -s {} push {} {}".format(
            self.adb_path, self.adb_device_id, local_path, remote_path))

    def pull(self, remote_path: str, local_path: str):
        assert 0 == os.system("{} -s {} pull {} {}".format(
            self.adb_path, self.adb_device_id, remote_path, local_path))

    def shell(self, shell: str):
        p = subprocess.Popen(
            [self.adb_path, "-s", self.adb_device_id, "shell", "su" if self.su else ""],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        return p.communicate(bytes(shell, 'utf-8'))[0].decode('utf-8')


class Android:
    def __init__(self, adb: Adb) -> None:
        self.adb = adb

    def boolean(self, s) -> bool:
        num = self.adb.shell(f"if [ {s} ]; then echo 1; else echo 0; fi")
        return int(num) == 1

    def query_battery(self):
        s = self.adb.shell("dumpsys battery")
        ans = s.split('\n')
        ans = map(lambda s: list(map(lambda s: s.strip(), s.split(':'))), ans)
        ans = filter(lambda arr: len(arr) >= 2 and len(arr[1]) >= 1, ans)
        return {key: value for key, value in ans}

    def total_cpus(self):
        s = self.adb.shell("ls /sys/devices/system/cpu")
        files = s.split('\n')
        total = 0
        for file in files:
            if file.startswith("cpu"):
                idx = ord(file[3]) - ord('0')
                total += int(0 <= idx and idx <= 9)
        return total

    def set_cpu_freq(self, cpu_idx, freq):
        cpu_freq_path = f"/sys/devices/system/cpu/cpu{cpu_idx}/cpufreq"

        self.adb.shell(f"echo 'userspace' > {cpu_freq_path}/scaling_governor")
        for file in ["scaling_min_freq", "scaling_max_freq", "scaling_setspeed"]:
            self.adb.shell(f"echo {freq} > {cpu_freq_path}/{file}")

        return int(self.adb.shell(f"cat {cpu_freq_path}/cpuinfo_cur_freq"))

    def get_related_cpus(self, cpu_idx):
        cpu_freq_path = f"/sys/devices/system/cpu/cpu{cpu_idx}/cpufreq"
        related_cpus = self.adb.shell(f"cat {cpu_freq_path}/related_cpus")
        related_cpus = related_cpus.split(' ')
        related_cpus = [
            int(cpu) for cpu in related_cpus if len(cpu.strip()) >= 1]
        return sorted(related_cpus)

    def get_available_frequencies(self, cpu_idx):
        cpu_freq_path = f"/sys/devices/system/cpu/cpu{cpu_idx}/cpufreq"
        available_frequencies = self.adb.shell(
            f"cat {cpu_freq_path}/scaling_available_frequencies")
        available_frequencies = available_frequencies.split(' ')
        available_frequencies = [
            int(freq) for freq in available_frequencies if len(freq.strip()) >= 1]
        return sorted(available_frequencies)

    def inspect_freq(self):
        dic = {}
        for i in range(self.total_cpus()):
            cpu_freq_path = f"/sys/devices/system/cpu/cpu{i}/cpufreq"
            related_cpus = self.get_related_cpus(i)
            if related_cpus[0] != i:
                continue
            freq = int(self.adb.shell(f"cat {cpu_freq_path}/cpuinfo_cur_freq"))
            governor = self.adb.shell(
                f"cat {cpu_freq_path}/scaling_governor").strip()
            dic[i] = {
                "freq": freq,
                "governor": governor,
                "available_frequencies": self.get_available_frequencies(i),
                "related_cpus": related_cpus
            }

        return dic

    def push_to_max_freq(self):
        freq = self.inspect_freq()
        for i in freq.keys():
            max_freq = freq[i]["available_frequencies"][-1]
            self.set_cpu_freq(i, max_freq)

    def _monitor_cpu_loop(self, file, queue: mp.Queue):
        with open(file, "w") as f:
            writer = csv.writer(f)
            first_time = True
            while queue.empty():
                freq = self.inspect_freq()
                if first_time:
                    row = ["time"]
                    for key in freq:
                        row.append(f"cpu{key}_freq")
                    writer.writerow(row)
                row = [str(datetime.datetime.now())]
                for key in freq:
                    row.append(freq[key]["freq"])
                writer.writerow(row)
                f.flush()
                first_time = False
            queue.get()
            queue.close()

    def start_monitor_cpu(self, file):
        self._monitor_cpu_queue = mp.Queue()
        self._monitor_cpu_process = mp.Process(
            target=self._monitor_cpu_loop,
            args=(file, self._monitor_cpu_queue)
        )
        self._monitor_cpu_process.start()

    def stop_monitor_cpu(self):
        self._monitor_cpu_queue.put(None)
        self._monitor_cpu_queue.close()
        self._monitor_cpu_process.join()

    @property
    def product_model(self):
        return self.adb.shell("getprop ro.product.model").strip()
