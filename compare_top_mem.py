#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import shutil
from memory_utils import parse_memory_value
from datetime import datetime
from pathlib import Path

def parse_top_file(filename):
    """解析top输出文件，返回PID到内存使用的映射"""
    mem_dict = {}
    with open(filename, 'r') as f:
        for line in f:
            if not line.strip() or line.startswith('top') or line.startswith('Tasks') or line.startswith('%Cpu') or line.startswith('MiB'):
                continue
            
            parts = line.split()
            if len(parts) < 12 or not parts[0].isdigit():
                continue
                
            pid = int(parts[0])
            mem = parse_memory_value(parts[5])  # RES列
            cmd = ' '.join(parts[11:])  # 完整命令行
            mem_dict[pid] = {'mem': mem, 'cmd': cmd}
    
    return mem_dict

def compare_memory(file1, file2):
    """比较两个时间点的内存使用变化"""
    mem_dict1 = parse_top_file(file1)
    mem_dict2 = parse_top_file(file2)
    
    changes = []
    
    # 比较相同PID的内存变化
    for pid in mem_dict1:
        if pid in mem_dict2:
            mem1 = mem_dict1[pid]['mem']
            mem2 = mem_dict2[pid]['mem']
            if mem1 != mem2:  # 只记录有变化的
                change = mem2 - mem1
                # 计算变化率，避免除以0
                change_rate = (change / mem1 * 100) if mem1 > 0 else float('inf')
                changes.append({
                    'pid': pid,
                    'cmd': mem_dict1[pid]['cmd'],
                    'mem1': mem1,
                    'mem2': mem2,
                    'change': change,
                    'change_rate': change_rate
                })
    
    return sorted(changes, key=lambda x: abs(x['change']), reverse=True)

def find_new_processes(file1, file2):
    """查找新增的进程"""
    def get_processes(filename):
        """从快照文件中获取所有进程信息"""
        processes = {}
        with open(filename, 'r') as f:
            for line in f:
                if not line.strip() or line.startswith('top') or line.startswith('Tasks') or line.startswith('%Cpu') or line.startswith('MiB'):
                    continue
                
                parts = line.split()
                if len(parts) < 12 or not parts[0].isdigit():
                    continue
                    
                pid = int(parts[0])
                mem = parse_memory_value(parts[5])
                cmd = ' '.join(parts[11:])
                processes[pid] = {'mem': mem, 'cmd': cmd}
        return processes
    
    # 获取两个文件中的进程信息
    procs1 = get_processes(file1)
    procs2 = get_processes(file2)
    
    # 找出新增的进程
    new_procs = []
    for pid, info in procs2.items():
        if pid not in procs1 and info['mem'] > 0:
            new_procs.append({
                'pid': pid,
                'mem_kb': info['mem'],
                'mem_mb': round(info['mem'] / 1024, 2),
                'mem_gb': round(info['mem'] / (1024 * 1024), 2),
                'cmd': info['cmd']
            })
    
    # 按内存使用量排序
    new_procs.sort(key=lambda x: x['mem_kb'], reverse=True)
    return new_procs

def format_new_processes_table(new_procs):
    """格式化输出新增进程的表格"""
    if not new_procs:
        return "\n没有发现新增进程\n"
    
    # 计算每列的最大宽度
    pid_width = max(len(str(p['pid'])) for p in new_procs)
    pid_width = max(pid_width, len('PID'))
    mem_kb_width = max(len(f"{p['mem_kb']:.1f}") for p in new_procs)
    mem_kb_width = max(mem_kb_width, len('Memory (KB)'))
    mem_mb_width = max(len(f"{p['mem_mb']:.1f}") for p in new_procs)
    mem_mb_width = max(mem_mb_width, len('Memory (MB)'))
    mem_gb_width = max(len(f"{p['mem_gb']:.2f}") for p in new_procs)
    mem_gb_width = max(mem_gb_width, len('Memory (GB)'))
    
    # 生成表格内容
    lines = []
    lines.append("\n新增进程列表:")
    separator = "-" * (pid_width + mem_kb_width + mem_mb_width + mem_gb_width + 50)
    lines.append(separator)
    
    # 表头
    header = (f"{'PID':<{pid_width}} {'Memory (KB)':<{mem_kb_width}} "
             f"{'Memory (MB)':<{mem_mb_width}} {'Memory (GB)':<{mem_gb_width}} {'Command'}")
    lines.append(header)
    lines.append(separator)
    
    # 进程信息
    for proc in new_procs:
        line = (f"{proc['pid']:<{pid_width}} {proc['mem_kb']:<{mem_kb_width}.1f} "
                f"{proc['mem_mb']:<{mem_mb_width}.1f} {proc['mem_gb']:<{mem_gb_width}.2f} {proc['cmd']}")
        lines.append(line)
    
    lines.append(separator)
    return "\n".join(lines)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='比较两个top快照文件中进程的内存变化情况')
    parser.add_argument('file1', help='第一个top输出文件')
    parser.add_argument('file2', help='第二个top输出文件')
    parser.add_argument('--no-trunc', action='store_true', help='不截断命令行输出')
    parser.add_argument('--show-new', action='store_true', help='显示新增进程')
    return parser.parse_args()

def format_output(changes, no_trunc=False):
    """格式化输出结果"""
    # 获取终端宽度
    terminal_width = shutil.get_terminal_size().columns
    
    # 计算命令行列的宽度
    fixed_width = 8 + 20 + 10 + 20 + 20 + 2  # 调整其他列的固定宽度
    cmd_width = terminal_width - fixed_width if no_trunc else 60
    
    # 打印表头
    print("进程内存变化情况分析:")
    print("-" * terminal_width)
    header = (f"{'PID':<8} {'内存变化':<20} {'变化率(%)':<10} "
             f"{'原始内存':<20} {'现在内存':<20} {'命令行':<{cmd_width}}")
    subheader = (f"{'':<8} {'(KB/GB)':<20} {'':<10} "
                f"{'(KB/GB)':<20} {'(KB/GB)':<20} {'':<{cmd_width}}")
    print(header)
    print(subheader)
    print("-" * terminal_width)
    
    # 打印数据行
    for item in changes:
        cmd = item['cmd'] if no_trunc else item['cmd'][:cmd_width]
        # 转换为GB
        change_gb = item['change'] / (1024 * 1024)
        mem1_gb = item['mem1'] / (1024 * 1024)
        mem2_gb = item['mem2'] / (1024 * 1024)
        
        # 格式化输出，根据值的大小选择合适的格式
        if abs(change_gb) < 0.01:
            change_str = f"{item['change']:+.1f}K"
        else:
            change_str = f"{item['change']:+.1f}K/{change_gb:+.3f}G"
            
        if mem1_gb < 0.01:
            mem1_str = f"{item['mem1']:.1f}K"
        else:
            mem1_str = f"{item['mem1']:.1f}K/{mem1_gb:.3f}G"
            
        if mem2_gb < 0.01:
            mem2_str = f"{item['mem2']:.1f}K"
        else:
            mem2_str = f"{item['mem2']:.1f}K/{mem2_gb:.3f}G"
        
        print(f"{item['pid']:<8} "
              f"{change_str:<20} "
              f"{item['change_rate']:+9.1f} "
              f"{mem1_str:<20} "
              f"{mem2_str:<20} "
              f"{cmd:<{cmd_width}}")

def parse_timestamp_from_filename(filename):
    """从文件名解析时间戳"""
    try:
        basename = Path(filename).name
        date_time_str = basename.replace('top_', '').replace('.txt', '')
        return datetime.strptime(date_time_str, '%Y%m%d_%H%M')
    except ValueError:
        return None

def ensure_time_order(file1, file2):
    """确保文件按时间顺序排列，返回正确顺序的文件名元组"""
    time1 = parse_timestamp_from_filename(file1)
    time2 = parse_timestamp_from_filename(file2)
    
    if time1 is None or time2 is None:
        raise ValueError("无法从文件名解析时间戳，请确保文件名格式为 'top_YYYYMMDD_HHMM.txt'")
    
    # 如果第一个文件时间晚于第二个文件，交换顺序
    if time1 > time2:
        print(f"警告: 输入文件顺序已调整以确保时间顺序\n"
              f"较早时间: {file2} ({time2})\n"
              f"较晚时间: {file1} ({time1})\n")
        return file2, file1
    
    return file1, file2

def main():
    args = parse_args()
    
    try:
        # 确保文件按时间顺序排列
        file1, file2 = ensure_time_order(args.file1, args.file2)
        
        # 比较内存变化
        changes = compare_memory(file1, file2)
        format_output(changes, args.no_trunc)
        
        # 如果指定了--show-new参数，显示新增进程
        if args.show_new:
            new_procs = find_new_processes(file1, file2)
            print(format_new_processes_table(new_procs))
            
    except FileNotFoundError as e:
        print(f"错误: 文件不存在 - {e.filename}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main() 