#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
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
    try:
        basename = Path(filename).name
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
            cmd_name = process_info['cmd']
            data.append({
                'timestamp': timestamp,
                'mem_mb': process_info['mem'] / 1024,  # 转换为MB
                'cmd': process_info['cmd']
            })
    
    return data, cmd_name

def plot_memory_usage(data, pid, output_file, img_format='png', dpi=300):
    """生成内存使用时间序列图"""
    if not data:
        print("没有数据可绘制", file=sys.stderr)
        return
    
    # 提取数据
    timestamps = [entry['timestamp'] for entry in data]
    memory_mb = [entry['mem_mb'] for entry in data]
    cmd = data[0]['cmd']
    
    # 创建图表
    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, memory_mb, marker='o', linestyle='-', linewidth=1, markersize=4)
    
    # 设置标题和标签
    plt.title(f'PID {pid}\n{cmd}', pad=20)
    plt.xlabel('Time')
    plt.ylabel('Memory Usage (MB)')
    
    # 设置x轴格式
    plt.gca().xaxis.set_major_formatter(DateFormatter('%Y-%m-%d %H:%M'))
    plt.gcf().autofmt_xdate()  # 自动旋转日期标签
    
    # 添加网格
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图片
    plt.savefig(output_file, format=img_format, dpi=dpi, bbox_inches='tight')
    plt.close()

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='生成进程内存使用时间序列图')
    parser.add_argument('--data', required=True, help='top快照文件所在目录')
    parser.add_argument('--pid', type=int, required=True, help='要跟踪的进程PID')
    parser.add_argument('-o', '--output', required=True, help='输出图片文件路径')
    parser.add_argument('--format', choices=['png', 'jpeg'], default='png', help='图片格式(png或jpeg)')
    parser.add_argument('--dpi', type=int, default=300, help='图片DPI(默认300)')
    return parser.parse_args()

def main():
    args = parse_args()
    
    try:
        # 收集数据
        data, cmd_name = collect_memory_data(args.data, args.pid)
        
        if not data:
            print(f"在快照中未找到PID {args.pid}的数据", file=sys.stderr)
            sys.exit(1)
        
        # 生成图表
        plot_memory_usage(data, args.pid, args.output, args.format, args.dpi)
        print(f"图片已保存到: {args.output}")
            
    except FileNotFoundError as e:
        print(f"错误: 文件或目录不存在 - {e.filename}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main() 