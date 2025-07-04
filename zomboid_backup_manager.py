#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zomboid 存档备份与恢复管理器
功能：
1. 备份Zomboid存档到指定目录
2. 浏览和恢复历史备份
3. 自动清理旧备份
4. 图形化用户界面
"""

import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import threading
import json
import time
import sys


class ZomboidBackupManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Zomboid 存档备份管理器")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 默认配置
        self.config = {
            "source_path": r"C:\Users\Administrator\Zomboid\Saves\Sandbox",
            "backup_root": r"D:\backup",
            "max_backups": 10,
            "auto_backup_enabled": False,
            "auto_backup_interval": 30  # 分钟
        }
        
        # 定时器相关
        self.auto_backup_timer = None
        self.auto_backup_active = False
        
        # 加载配置
        self.load_config()
        
        # 创建界面
        self.create_widgets()
        
        # 刷新备份列表
        self.refresh_backup_list()
    
        # 如果配置中启用了自动备份，则自动启动
        if self.config["auto_backup_enabled"]:
            self.start_auto_backup()
    
    def get_resource_path(relative_path):
        """获取资源文件路径，兼容打包后的exe"""
        try:
            # PyInstaller创建临时文件夹并存储路径在_MEIPASS中
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        
        return os.path.join(base_path, relative_path)

    def load_config(self):
        """加载配置文件"""
        config_file = "config.json"
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
        except Exception as e:
            print(f"加载配置失败: {e}")
    
    def save_config(self):
        """保存配置文件"""
        try:
            # 保存到exe同目录下
            config_file = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else '.', 'config.json')
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def create_widgets(self):
        """创建GUI组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="Zomboid 存档备份管理器", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 配置区域
        config_frame = ttk.LabelFrame(main_frame, text="配置设置", padding="10")
        config_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        # 源目录
        ttk.Label(config_frame, text="存档目录:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.source_var = tk.StringVar(value=self.config["source_path"])
        source_entry = ttk.Entry(config_frame, textvariable=self.source_var, width=50)
        source_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=2)
        ttk.Button(config_frame, text="浏览", 
                  command=self.browse_source).grid(row=0, column=2, pady=2)
        
        # 备份目录
        ttk.Label(config_frame, text="备份目录:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.backup_var = tk.StringVar(value=self.config["backup_root"])
        backup_entry = ttk.Entry(config_frame, textvariable=self.backup_var, width=50)
        backup_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=2)
        ttk.Button(config_frame, text="浏览", 
                  command=self.browse_backup).grid(row=1, column=2, pady=2)
        
        # 最大备份数
        ttk.Label(config_frame, text="保留备份数:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.max_backups_var = tk.StringVar(value=str(self.config["max_backups"]))
        max_backups_entry = ttk.Entry(config_frame, textvariable=self.max_backups_var, width=10)
        max_backups_entry.grid(row=2, column=1, sticky=tk.W, padx=(10, 5), pady=2)
        
        # 自动备份设置
        auto_frame = ttk.Frame(config_frame)
        auto_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.auto_backup_var = tk.BooleanVar(value=self.config["auto_backup_enabled"])
        auto_check = ttk.Checkbutton(auto_frame, text="启用定时自动备份", 
                                   variable=self.auto_backup_var,
                                   command=self.toggle_auto_backup)
        auto_check.pack(side=tk.LEFT)
        
        ttk.Label(auto_frame, text="间隔(分钟):").pack(side=tk.LEFT, padx=(20, 5))
        self.auto_interval_var = tk.StringVar(value=str(self.config["auto_backup_interval"]))
        interval_entry = ttk.Entry(auto_frame, textvariable=self.auto_interval_var, width=8)
        interval_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        self.auto_status_label = ttk.Label(auto_frame, text="", foreground="green")
        self.auto_status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 操作按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        self.backup_btn = ttk.Button(button_frame, text="立即备份", 
                                    command=self.start_backup, style="Accent.TButton")
        self.backup_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="刷新列表", 
                  command=self.refresh_backup_list).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="保存配置", 
                  command=self.save_current_config).pack(side=tk.LEFT)
        
        # 备份列表区域
        list_frame = ttk.LabelFrame(main_frame, text="备份历史", padding="10")
        list_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # 创建Treeview
        columns = ("name", "date", "size", "path")
        self.backup_tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", height=15)
        self.backup_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 设置列
        self.backup_tree.heading("#0", text="备份名称")
        self.backup_tree.heading("name", text="文件夹名")
        self.backup_tree.heading("date", text="创建时间")
        self.backup_tree.heading("size", text="大小")
        self.backup_tree.heading("path", text="路径")
        
        self.backup_tree.column("#0", width=200)
        self.backup_tree.column("name", width=150)
        self.backup_tree.column("date", width=150)
        self.backup_tree.column("size", width=100)
        self.backup_tree.column("path", width=300)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.backup_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.backup_tree.configure(yscrollcommand=scrollbar.set)
        
        # 右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="恢复此备份", command=self.restore_selected)
        self.context_menu.add_command(label="删除此备份", command=self.delete_selected)
        self.context_menu.add_command(label="打开备份文件夹", command=self.open_backup_folder)
        
        self.backup_tree.bind("<Button-3>", self.show_context_menu)
        self.backup_tree.bind("<Double-1>", self.restore_selected)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Bug反馈联系信息
        contact_label = ttk.Label(main_frame, text="遇到BUG请联系: zhounan36@163.com", 
                                 font=("Arial", 8), foreground="gray")
        contact_label.grid(row=6, column=0, columnspan=3, pady=(5, 0))
    
    def browse_source(self):
        """浏览源目录"""
        directory = filedialog.askdirectory(title="选择Zomboid存档目录")
        if directory:
            self.source_var.set(directory)
    
    def browse_backup(self):
        """浏览备份目录"""
        directory = filedialog.askdirectory(title="选择备份根目录")
        if directory:
            self.backup_var.set(directory)
    
    def save_current_config(self):
        """保存当前配置"""
        try:
            self.config["source_path"] = self.source_var.get()
            self.config["backup_root"] = self.backup_var.get()
            self.config["max_backups"] = int(self.max_backups_var.get())
            self.config["auto_backup_enabled"] = self.auto_backup_var.get()
            self.config["auto_backup_interval"] = int(self.auto_interval_var.get())
            self.save_config()
            self.status_var.set("配置已保存")
            messagebox.showinfo("成功", "配置已保存!")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的备份数量和时间间隔!")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")
    
    def get_folder_size(self, folder_path):
        """计算文件夹大小"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
            return total_size
        except Exception:
            return 0
    
    def format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def safe_copy_file(self, src, dst):
        """复制单个文件，即使文件被占用也强制复制"""
        try:
            # 创建目标目录
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            
            # 直接复制文件，不检查占用状态
            shutil.copy2(src, dst)
            return True
            
        except Exception as e:
            print(f"复制文件失败 {src} -> {dst}: {e}")
            return False
    
    def safe_copytree(self, src, dst):
        """安全复制目录树，强制复制所有文件"""
        copied_files = 0
        failed_files = 0
        
        try:
            # 创建目标根目录
            os.makedirs(dst, exist_ok=True)
            
            # 遍历源目录
            for root, dirs, files in os.walk(src):
                # 计算相对路径
                rel_path = os.path.relpath(root, src)
                if rel_path == '.':
                    dst_dir = dst
                else:
                    dst_dir = os.path.join(dst, rel_path)
                
                # 创建目录
                os.makedirs(dst_dir, exist_ok=True)
                
                # 复制文件
                for file in files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(dst_dir, file)
                    
                    # 直接复制文件
                    if self.safe_copy_file(src_file, dst_file):
                        copied_files += 1
                    else:
                        failed_files += 1
                        print(f"文件复制失败: {src_file}")
            
            print(f"复制完成: 成功 {copied_files} 个文件, 失败 {failed_files} 个文件")
            return failed_files == 0
            
        except Exception as e:
            print(f"目录复制失败: {e}")
            return False
    
    def refresh_backup_list(self):
        """刷新备份列表"""
        # 清空现有列表
        for item in self.backup_tree.get_children():
            self.backup_tree.delete(item)
        
        backup_root = self.backup_var.get()
        if not os.path.exists(backup_root):
            self.status_var.set("备份目录不存在")
            return
        
        try:
            # 获取所有备份文件夹
            backup_folders = []
            for item in os.listdir(backup_root):
                item_path = os.path.join(backup_root, item)
                if os.path.isdir(item_path) and item.startswith("Zomboid_Backup_"):
                    backup_folders.append(item_path)
            
            # 按创建时间排序
            backup_folders.sort(key=lambda x: os.path.getctime(x), reverse=True)
            
            # 添加到列表
            for folder_path in backup_folders:
                folder_name = os.path.basename(folder_path)
                create_time = datetime.fromtimestamp(os.path.getctime(folder_path))
                size = self.get_folder_size(folder_path)
                
                self.backup_tree.insert("", "end", 
                                       text=folder_name,
                                       values=(
                                           folder_name,
                                           create_time.strftime("%Y-%m-%d %H:%M:%S"),
                                           self.format_size(size),
                                           folder_path
                                       ))
            
            self.status_var.set(f"找到 {len(backup_folders)} 个备份")
            
        except Exception as e:
            messagebox.showerror("错误", f"刷新备份列表失败: {e}")
            self.status_var.set("刷新失败")
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        item = self.backup_tree.selection()
        if item:
            self.context_menu.post(event.x_root, event.y_root)
    
    def start_backup(self):
        """开始备份（在后台线程中执行）"""
        self.backup_btn.config(state="disabled")
        self.progress.start()
        self.status_var.set("正在备份...")
        
        thread = threading.Thread(target=self.perform_backup)
        thread.daemon = True
        thread.start()
    
    def perform_backup(self):
        """执行备份操作"""
        try:
            source_path = self.source_var.get()
            backup_root = self.backup_var.get()
            
            # 检查源目录
            if not os.path.exists(source_path):
                self.root.after(0, lambda: messagebox.showerror("错误", f"源目录不存在: {source_path}"))
                return
            
            # 创建备份根目录
            os.makedirs(backup_root, exist_ok=True)
            
            # 生成时间戳文件夹名
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_destination = os.path.join(backup_root, f"Zomboid_Backup_{timestamp}")
            
            # 使用安全复制方法复制文件
            self.root.after(0, lambda: self.status_var.set("正在复制文件..."))
            success = self.safe_copytree(source_path, backup_destination)
            
            if not success:
                self.root.after(0, lambda: messagebox.showwarning("警告", "部分文件复制失败，请检查备份完整性"))
            
            # 计算备份大小
            backup_size = self.get_folder_size(backup_destination)
            
            # 清理旧备份
            self.cleanup_old_backups()
            
            # 更新UI
            self.root.after(0, self.backup_completed, backup_destination, backup_size)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"备份失败: {e}"))
            self.root.after(0, self.backup_failed)
    
    def backup_completed(self, backup_path, backup_size):
        """备份完成后的UI更新"""
        self.progress.stop()
        self.backup_btn.config(state="normal")
        self.status_var.set(f"备份完成! 大小: {self.format_size(backup_size)}")
        self.refresh_backup_list()
        messagebox.showinfo("成功", f"备份完成!\n路径: {backup_path}\n大小: {self.format_size(backup_size)}")
    
    def backup_failed(self):
        """备份失败后的UI更新"""
        self.progress.stop()
        self.backup_btn.config(state="normal")
        self.status_var.set("备份失败")
    
    def cleanup_old_backups(self):
        """清理旧备份"""
        try:
            backup_root = self.backup_var.get()
            max_backups = int(self.max_backups_var.get())
            
            # 获取所有备份文件夹
            backup_folders = []
            for item in os.listdir(backup_root):
                item_path = os.path.join(backup_root, item)
                if os.path.isdir(item_path) and item.startswith("Zomboid_Backup_"):
                    backup_folders.append(item_path)
            
            # 按创建时间排序，保留最新的
            backup_folders.sort(key=lambda x: os.path.getctime(x), reverse=True)
            
            # 删除多余的备份
            if len(backup_folders) > max_backups:
                for old_backup in backup_folders[max_backups:]:
                    shutil.rmtree(old_backup)
                    print(f"已删除旧备份: {os.path.basename(old_backup)}")
                    
        except Exception as e:
            print(f"清理旧备份失败: {e}")
    
    def restore_selected(self, event=None):
        """恢复选中的备份"""
        selection = self.backup_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要恢复的备份!")
            return
        
        item = selection[0]
        backup_path = self.backup_tree.item(item)["values"][3]
        backup_name = self.backup_tree.item(item)["text"]
        
        # 确认对话框
        result = messagebox.askyesno("确认恢复", 
                                   f"确定要恢复备份 '{backup_name}' 吗?\n\n"
                                   f"这将覆盖当前的存档文件!")
        
        if result:
            self.perform_restore(backup_path, backup_name)
    
    def perform_restore(self, backup_path, backup_name):
        """执行恢复操作"""
        try:
            source_path = self.source_var.get()
            
            # 备份当前存档（以防恢复失败）
            if os.path.exists(source_path):
                backup_current = f"{source_path}_backup_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copytree(source_path, backup_current)
                print(f"已备份当前存档到: {backup_current}")
            
            # 删除当前存档
            if os.path.exists(source_path):
                shutil.rmtree(source_path)
            
            # 恢复备份
            # 找到备份内的Sandbox文件夹
            sandbox_path = None
            for item in os.listdir(backup_path):
                item_path = os.path.join(backup_path, item)
                if os.path.isdir(item_path) and item == "Sandbox":
                    sandbox_path = item_path
                    break
            
            if sandbox_path:
                shutil.copytree(sandbox_path, source_path)
            else:
                # 如果没找到Sandbox文件夹，直接复制整个备份
                shutil.copytree(backup_path, source_path)
            
            self.status_var.set(f"已恢复备份: {backup_name}")
            messagebox.showinfo("成功", f"备份 '{backup_name}' 已成功恢复!")
            
        except Exception as e:
            messagebox.showerror("错误", f"恢复备份失败: {e}")
            self.status_var.set("恢复失败")
    
    def delete_selected(self):
        """删除选中的备份"""
        selection = self.backup_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的备份!")
            return
        
        item = selection[0]
        backup_path = self.backup_tree.item(item)["values"][3]
        backup_name = self.backup_tree.item(item)["text"]
        
        # 确认对话框
        result = messagebox.askyesno("确认删除", 
                                   f"确定要删除备份 '{backup_name}' 吗?\n\n"
                                   f"此操作不可撤销!")
        
        if result:
            try:
                shutil.rmtree(backup_path)
                self.refresh_backup_list()
                self.status_var.set(f"已删除备份: {backup_name}")
                messagebox.showinfo("成功", f"备份 '{backup_name}' 已删除!")
            except Exception as e:
                messagebox.showerror("错误", f"删除备份失败: {e}")
    
    def open_backup_folder(self):
        """打开备份文件夹"""
        selection = self.backup_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择备份!")
            return
        
        item = selection[0]
        backup_path = self.backup_tree.item(item)["values"][3]
        
        try:
            os.startfile(backup_path)
        except Exception as e:
            messagebox.showerror("错误", f"打开文件夹失败: {e}")
    
    def toggle_auto_backup(self):
        """切换自动备份状态"""
        if self.auto_backup_var.get():
            self.start_auto_backup()
        else:
            self.stop_auto_backup()
    
    def start_auto_backup(self):
        """启动自动备份"""
        try:
            interval = int(self.auto_interval_var.get())
            if interval <= 0:
                messagebox.showerror("错误", "时间间隔必须大于0!")
                self.auto_backup_var.set(False)
                return
            
            self.auto_backup_active = True
            self.schedule_next_backup()
            self.auto_status_label.config(text=f"自动备份已启动 (每{interval}分钟)", foreground="green")
            self.status_var.set(f"自动备份已启动，间隔: {interval}分钟")
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的时间间隔!")
            self.auto_backup_var.set(False)
        except Exception as e:
            messagebox.showerror("错误", f"启动自动备份失败: {e}")
            self.auto_backup_var.set(False)
    
    def stop_auto_backup(self):
        """停止自动备份"""
        self.auto_backup_active = False
        if self.auto_backup_timer:
            self.root.after_cancel(self.auto_backup_timer)
            self.auto_backup_timer = None
        
        self.auto_status_label.config(text="自动备份已停止", foreground="red")
        self.status_var.set("自动备份已停止")
    
    def schedule_next_backup(self):
        """安排下次自动备份"""
        if not self.auto_backup_active:
            return
        
        try:
            interval = int(self.auto_interval_var.get())
            interval_ms = interval * 60 * 1000  # 转换为毫秒
            
            self.auto_backup_timer = self.root.after(interval_ms, self.auto_backup_callback)
            
        except ValueError:
            self.stop_auto_backup()
            messagebox.showerror("错误", "无效的时间间隔设置!")
    
    def auto_backup_callback(self):
        """自动备份回调函数"""
        if not self.auto_backup_active:
            return
        
        # 执行自动备份
        self.status_var.set("正在执行自动备份...")
        thread = threading.Thread(target=self.perform_auto_backup)
        thread.daemon = True
        thread.start()
    
    def perform_auto_backup(self):
        """执行自动备份（不显示进度条）"""
        try:
            source_path = self.source_var.get()
            backup_root = self.backup_var.get()
            
            # 检查源目录
            if not os.path.exists(source_path):
                self.root.after(0, lambda: self.status_var.set(f"自动备份失败: 源目录不存在"))
                self.root.after(0, self.schedule_next_backup)
                return
            
            # 创建备份根目录
            os.makedirs(backup_root, exist_ok=True)
            
            # 生成时间戳文件夹名
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_destination = os.path.join(backup_root, f"Zomboid_Backup_{timestamp}")
            
            # 使用安全复制方法复制文件
            success = self.safe_copytree(source_path, backup_destination)
            
            if not success:
                self.root.after(0, lambda: self.status_var.set("自动备份完成但部分文件复制失败"))
            
            # 计算备份大小
            backup_size = self.get_folder_size(backup_destination)
            
            # 清理旧备份
            self.cleanup_old_backups()
            
            # 更新UI
            self.root.after(0, self.auto_backup_completed, backup_destination, backup_size)
            
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"自动备份失败: {e}"))
            self.root.after(0, self.schedule_next_backup)
    
    def auto_backup_completed(self, backup_path, backup_size):
        """自动备份完成后的UI更新"""
        backup_name = os.path.basename(backup_path)
        self.status_var.set(f"自动备份完成: {backup_name} ({self.format_size(backup_size)})")
        self.refresh_backup_list()
        
        # 安排下次备份
        self.schedule_next_backup()

    def run(self):
        """运行应用程序"""
        self.root.mainloop()


if __name__ == "__main__":
    app = ZomboidBackupManager()
    app.run()
