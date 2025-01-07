#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def parse_memory_value(mem_str):
    """
    解析内存值，将不同单位统一转换为KB
    支持的单位：k(KB), m(MB), g(GB)
    不带单位时默认为KB
    """
    try:
        # 移除空格并转换为小写
        mem_str = str(mem_str).strip().lower()
        
        # 如果是纯数字，默认单位为KB
        if mem_str.replace('.', '').isdigit():
            return float(mem_str)
            
        # 获取数值和单位
        if mem_str.endswith('k'):
            return float(mem_str[:-1])
        elif mem_str.endswith('m'):
            return float(mem_str[:-1]) * 1024
        elif mem_str.endswith('g'):
            return float(mem_str[:-1]) * 1024 * 1024
        else:
            # 如果没有识别出单位，默认为KB
            return float(mem_str)
    except (ValueError, AttributeError):
        raise ValueError(f"无法解析内存值: {mem_str}") 