import re
import csv
from datetime import datetime, date
from collections import defaultdict
import json
import argparse
from script_petasense import find_port
import serial
import time

class LogAnalyzer:
    def __init__(self, file_name, json_file):
        self.file_name = file_name
        self.json_file = json_file
        self.list_of_logs = self.get_log_lines(file_name)
        self.times_taken = []

    def get_log_lines(self, file_name):
        with open(file_name, 'r') as file_handle:
            list_of_logs = file_handle.readlines()
        return list_of_logs

    def get_datetime_obj(self, log):
        log_time = log[10:22]
        time_obj = datetime.strptime(log_time, '%H:%M:%S.%f').time()
        return time_obj

    def get_time(self, start_log, end_log):
        start_time = self.get_datetime_obj(start_log)
        end_time = self.get_datetime_obj(end_log)
        duration = datetime.combine(date.min, end_time) - datetime.combine(date.min, start_time)
        return duration.total_seconds()

    def total_time(self):
        return self.get_time(self.list_of_logs[0], self.list_of_logs[-2])

    def write_to_csv(self, duration, file_name):
        with open(file_name, mode='w', newline='') as file:
            fieldnames = ['Module', 'Duration']
            writer = csv.writer(file)
            writer.writerow(fieldnames)
            writer.writerows(duration)

    def write_stats_to_csv(self, data_dict, filename):
        header = ['Module', 'max', 'min', 'avg']
        with open(filename, mode='w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)
            for category, stats in data_dict.items():
                row = [category, stats['max'], stats['min'], stats['avg']]
                writer.writerow(row)

    def calculate_module_statistics(self):
        module_stats = defaultdict(lambda: {'max': 0, 'min': float('inf'), 'sum': 0, 'count': 0})
        for row in self.times_taken:
            module = row[0]
            duration = float(row[1])
            stats = module_stats[module]
            stats['max'] = round(max(stats['max'], duration), 3)
            stats['min'] = round(min(stats['min'], duration), 3)
            stats['sum'] += duration
            stats['count'] += 1

        for module, stats in module_stats.items():
            stats['avg'] = round(stats['sum'] / stats['count'], 3)
        return module_stats

    def print_module_statistics(self, module_stats):
        module_list = []
        for module, stats in module_stats.items():
            module_list.append(module)
            print(f"Module: {module}")
            print(f"  Max Duration: {stats['max']:.3f}")
            print(f"  Min Duration: {stats['min']:.3f}")
            print(f"  Avg Duration: {stats['avg']:.3f}")
            print()
        return module_list

    def analyze_logs(self):
        tmr_pattern = re.compile(r'\[\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\]\[\w+\]\[tmr\]:')
        start_pattern = re.compile(r'\[\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\]\[\w+\]\[tmr\]: (start) (.*)')
        end_pattern = re.compile(r'\[\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\]\[\w+\]\[tmr\]: (end) (.*)')

        latest_start_log = None
        for log in self.list_of_logs:
            start_match = start_pattern.search(log)
            if start_match:
                latest_start_log = log
            else:
                end_match = end_pattern.search(log)
                if end_match and latest_start_log:
                    start_log = latest_start_log
                    end_log = log
                    duration = self.get_time(start_log, end_log)
                    self.times_taken.append([end_match.group(2), duration])
                    latest_start_log = None

    def calculate_battery_life(self, module_stats, module_list):
        with open(self.json_file) as f:
            data = json.load(f)
        totalcurrent = []
        print(module_list)
        for module in module_list:
            if(module in data):
                totalcurrent.append(module_stats[module]['sum'] * data[module])
        print(totalcurrent)
        #print(module_stats)
        if(len(totalcurrent)!=0):
            totalcurrent_day = sum(totalcurrent) / 3600
            no_of_hours = 1500 / totalcurrent_day
            return int(no_of_hours / 24)
        else:
            return 0

    def save_final_result(self, module_stats, module_list):
        with open(self.json_file) as f:
            data = json.load(f)

        fields = ['module', 'current', 'time', 'charge', 'no of days']
        filename = 'final_result.csv'
        mylist = []

        for module in module_list:
            charge_hour = data[module] * module_stats[module]['sum'] / 3600
            dict = {
                'module': module,
                'current': data[module],
                'time': module_stats[module]['sum'],
                'charge': data[module] * module_stats[module]['sum'],
                'no of days': (1500 / (charge_hour * 24))
            }
            mylist.append(dict)

        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(mylist)

    def run_analysis(self):
        self.analyze_logs()
        self.write_to_csv(self.times_taken, 'output.csv')
        module_stats = self.calculate_module_statistics()
        module_list = self.print_module_statistics(module_stats)
        self.write_stats_to_csv(module_stats, 'stats.csv')
        total_runtime = self.total_time()
        print(f"Total Runtime: {total_runtime:.2f} seconds")
        battery_life_days = self.calculate_battery_life(module_stats, module_list)
        print(f"Estimated Battery Life: {battery_life_days} days")
        self.save_final_result(module_stats, module_list)

class RealTimeLogAnalyzer:
    def __init__(self, json_file):
        self.json_file = json_file
        self.times_taken = []
        self.latest_start_log = None

    def get_datetime_obj(self, log):
        log_time = log[10:22]
        return datetime.strptime(log_time, '%H:%M:%S.%f').time()

    def get_time(self, start_log, end_log):
        start_time = self.get_datetime_obj(start_log)
        end_time = self.get_datetime_obj(end_log)
        duration = datetime.combine(date.min, end_time) - datetime.combine(date.min, start_time)
        return duration.total_seconds()

    def calculate_module_statistics(self):
        module_stats = defaultdict(lambda: {'max': 0, 'min': float('inf'), 'sum': 0, 'count': 0})
        for row in self.times_taken:
            module = row[0]
            duration = float(row[1])
            stats = module_stats[module.split("\r")[0]]
            stats['max'] = round(max(stats['max'], duration), 3)
            stats['min'] = round(min(stats['min'], duration), 3)
            stats['sum'] += duration
            stats['count'] += 1

        for stats in module_stats.values():
            stats['avg'] = round(stats['sum'] / stats['count'], 3)
        return module_stats

    def print_module_statistics(self, module_stats):
        module_list = []
        for module, stats in module_stats.items():
            module_list.append(module.split('\r')[0])
            print(f"Module: {module}")
            print(f"  Max Duration: {stats['max']:.3f}")
            print(f"  Min Duration: {stats['min']:.3f}")
            print(f"  Avg Duration: {stats['avg']:.3f}")
            print()
        return module_list

    def process_log(self, log):
        start_pattern = re.compile(r'\[\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\]\[\w+\]\[tmr\]: (start) (.*)')
        end_pattern = re.compile(r'\[\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\]\[\w+\]\[tmr\]: (end) (.*)')

        start_match = start_pattern.search(log)
        if start_match:
            self.latest_start_log = log
        else:
            end_match = end_pattern.search(log)
            if end_match and self.latest_start_log:
                start_log = self.latest_start_log
                end_log = log
                duration = self.get_time(start_log, end_log)
                self.times_taken.append([end_match.group(2), duration])
                self.latest_start_log = None
    def calculate_battery_life(self, module_stats, module_list):
        with open(self.json_file) as f:
            data = json.load(f)
        totalcurrent = []
        print(module_list)
        for module in module_list:
            if(module in data):
                totalcurrent.append(module_stats[module]['sum'] * data[module])
        print(totalcurrent)
        #print(module_stats)
        if(len(totalcurrent)!=0):
            totalcurrent_day = sum(totalcurrent) / 3600
            no_of_hours = 1500 / totalcurrent_day
            return int(no_of_hours / 24)
        else:
            return 0

    def run_analysis(self):
        module_stats = self.calculate_module_statistics()
        module_list = self.print_module_statistics(module_stats)
        return module_stats, module_list

def main():
    parser = argparse.ArgumentParser(description="Log Analyzer Program")
    parser.add_argument('mode', choices=['file', 'realtime'], help="Choose the mode: 'file' for file-based log analysis or 'realtime' for real-time log analysis")
    parser.add_argument('--logfile', help="Path to the log file (required for file mode)")
    parser.add_argument('--jsonfile', required=True, help="Path to the JSON file with module data")
    args = parser.parse_args()

    if args.mode == 'file':
        if not args.logfile:
            print("Error: Log file path is required for file mode.")
            return
        log_analyzer = LogAnalyzer(args.logfile, args.jsonfile)
        log_analyzer.run_analysis()
    elif args.mode == 'realtime':
        real_time_analyzer = RealTimeLogAnalyzer(args.jsonfile)
        #print("Start entering logs in real-time (type 'exit' to stop):")
        max_time=int(input("enter seconds you want to read the logs"))
        start_time=time.time()
        port=find_port()
        ser=serial.Serial(port,115200)
        end_time=datetime.datetime.fromtimestamp(time.time()+max_time)
        print(f"Program will end at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        while (time.time()-start_time<max_time):
            try:
                x=ser.readline()
                log=str(x,'UTF-8')
                #print(log)
                real_time_analyzer.process_log(log)
            except:
                ser.close()
            
            
        module_stats, module_list = real_time_analyzer.run_analysis()
        battery_life_days = real_time_analyzer.calculate_battery_life(module_stats, module_list)
        print(f"Estimated Battery Life: {battery_life_days} days")

if __name__ == "__main__":
    main()
