#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import os
import json
import csv
from datetime import datetime
from pathlib import Path
from memory_utils import parse_memory_value

def parse_top_file(filename, target_pid):
    """从top输出文件中解析指定PID的内存使用情况"""
    with open(filename, 'r') as f:
        for line in f:
            if not line.strip() or line.startswith('top') or line.startswith('Tasks') or line.startswith('%Cpu') or line.startswith('MiB'):
                continue
            
            parts = line.split()
            if len(parts) < 12 or not parts[0].isdigit():
                continue
                
            pid = int(parts[0])
            if pid == target_pid:
                return {
                    'pid': pid,
                    'mem': parse_memory_value(parts[5]),  # RES列，转换为KB
                    'cmd': ' '.join(parts[11:])  # 完整命令行
                }
    return None

def parse_timestamp_from_filename(filename):
    """从文件名解析时间戳"""
    # 假设文件名格式为: top_YYYYMMDD_HHMM.txt
    try:
        basename = os.path.basename(filename)
        date_time_str = basename.replace('top_', '').replace('.txt', '')
        return datetime.strptime(date_time_str, '%Y%m%d_%H%M')
    except ValueError:
        return None

def collect_memory_data(snapshots_dir, target_pid):
    """收集指定PID的内存使用数据"""
    data = []
    cmd_name = None
    
    # 获取所有snapshot文件并按时间排序
    snapshot_files = sorted(
        Path(snapshots_dir).glob('top_*.txt'),
        key=lambda x: parse_timestamp_from_filename(x)
    )
    
    for snapshot_file in snapshot_files:
        timestamp = parse_timestamp_from_filename(snapshot_file)
        if timestamp is None:
            continue
            
        process_info = parse_top_file(snapshot_file, target_pid)
        if process_info:
            cmd_name = process_info['cmd']  # 记录进程名
            data.append({
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M'),
                'pid': process_info['pid'],  # 添加PID信息
                'mem': process_info['mem'],
                'cmd': process_info['cmd']
            })
    
    return data, cmd_name

def output_json(data, output_file=None):
    """输出JSON格式数据"""
    json_data = json.dumps(data, indent=2, ensure_ascii=False)
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json_data)
    else:
        print(json_data)

def output_csv_row_based(data, output_file=None):
    """输出基于行的CSV格式数据"""
    if not data:
        print("没有数据可输出", file=sys.stderr)
        return
        
    # 获取进程基本信息
    process_info = {
        'PID': data[0]['pid'],
        'Command': data[0]['cmd']
    }
    
    # 准备CSV数据
    headers = ['timestamp', 'memory_kb', 'memory_mb', 'memory_gb']
    rows = [
        {
            'timestamp': entry['timestamp'],
            'memory_kb': entry['mem'],
            'memory_mb': round(entry['mem'] / 1024, 2),
            'memory_gb': round(entry['mem'] / (1024 * 1024), 2)
        }
        for entry in data
    ]
    
    def write_csv(f):
        writer = csv.writer(f)
        # 写入进程信息
        writer.writerow(['Process Information:', '', '', ''])  # 补充逗号使列数一致
        for key, value in process_info.items():
            writer.writerow([key, value, '', ''])  # 补充逗号使列数一致
        writer.writerow(['', '', '', ''])  # 空行，保持列数一致
        
        # 写入内存数据
        writer.writerow(['Memory Usage:', '', '', ''])  # 补充逗号使列数一致
        dict_writer = csv.DictWriter(f, fieldnames=headers)
        dict_writer.writeheader()
        dict_writer.writerows(rows)
    
    # 写入CSV
    if output_file:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            write_csv(f)
    else:
        write_csv(sys.stdout)

def output_csv_column_based(data, output_file=None):
    """输出基于列的CSV格式数据"""
    if not data:
        print("没有数据可输出", file=sys.stderr)
        return

    # 获取进程基本信息
    process_info = {
        'PID': data[0]['pid'],
        'Command': data[0]['cmd']
    }

    # 获取所有时间戳作为表头
    timestamps = [entry['timestamp'] for entry in data]
    
    # 准备数据行
    rows = [
        {
            'metric': 'memory_kb',
            **{entry['timestamp']: entry['mem'] for entry in data}
        },
        {
            'metric': 'memory_mb',
            **{entry['timestamp']: round(entry['mem'] / 1024, 2) for entry in data}
        },
        {
            'metric': 'memory_gb',
            **{entry['timestamp']: round(entry['mem'] / (1024 * 1024), 2) for entry in data}
        }
    ]

    # 定义表头
    headers = ['metric'] + timestamps

    def write_csv(f):
        writer = csv.writer(f)
        # 写入进程信息
        num_cols = len(timestamps) + 1  # metric列加上所有时间戳列
        writer.writerow(['Process Information:'] + [''] * (num_cols - 1))  # 补充逗号使列数一致
        for key, value in process_info.items():
            writer.writerow([key, value] + [''] * (num_cols - 2))  # 补充逗号使列数一致
        writer.writerow([''] * num_cols)  # 空行，保持列数一致
        
        # 写入内存数据
        writer.writerow(['Memory Usage:'] + [''] * (num_cols - 1))  # 补充逗号使列数一致
        dict_writer = csv.DictWriter(f, fieldnames=headers)
        dict_writer.writeheader()
        dict_writer.writerows(rows)

    # 写入CSV
    if output_file:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            write_csv(f)
    else:
        write_csv(sys.stdout)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='跟踪指定PID的内存使用情况')
    parser.add_argument('--data', required=True, help='top快照文件所在目录')
    parser.add_argument('--pid', type=int, required=True, help='要跟踪的进程PID')
    parser.add_argument('-o', '--output', choices=['json', 'csv'], required=True, help='输出格式')
    parser.add_argument('-f', '--file', help='输出文件路径，不指定则输出到标准输出')
    parser.add_argument('--format', choices=['row', 'column'], default='column', 
                      help='CSV输出格式：row(行格式)或column(列格式)，默认为column')
    return parser.parse_args()

def main():
    args = parse_args()
    
    try:
        # 收集数据
        data, cmd_name = collect_memory_data(args.data, args.pid)
        
        if not data:
            print(f"在快照中未找到PID {args.pid}的数据", file=sys.stderr)
            sys.exit(1)
            
        # 根据指定格式输出
        if args.output == 'json':
            output_json(data, args.file)
        else:  # csv
            if args.format == 'row':
                output_csv_row_based(data, args.file)
            else:
                output_csv_column_based(data, args.file)
            
    except FileNotFoundError as e:
        print(f"错误: 文件或目录不存在 - {e.filename}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main() 