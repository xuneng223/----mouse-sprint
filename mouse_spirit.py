import tkinter as tk
from tkinter import ttk, messagebox
import pyautogui
import time
import json
import os
import threading
import sys
import math

# 尝试导入pynput，如果失败则使用备用方案
try:
    from pynput import mouse
    from pynput import keyboard
    from pynput.keyboard import Key, KeyCode
    PYNPUT_AVAILABLE = True
except (ImportError, TypeError, AttributeError) as e:
    print(f"警告: pynput导入失败: {e}")
    print("将使用备用方法进行鼠标跟踪")
    PYNPUT_AVAILABLE = False

class MouseSpirit:
    # 定义颜色方案为类变量
    COLORS = {
        'bg': '#f5f6f7',  # 浅灰色背景
        'fg': '#2c3e50',  # 深色文字
        'accent': '#3498db',  # 蓝色强调色
        'button': '#ecf0f1',  # 按钮背景色
        'button_pressed': '#bdc3c7',  # 按钮按下时的颜色
        'tree_selected': '#d5e9f7',  # 树形列表选中项的背景色
        'frame_bg': '#ffffff'  # 框架背景色
    }

    def __init__(self, root):
        self.root = root
        self.root.title("鼠标精灵 (Mouse Spirit)")
        self.root.geometry("1300x600")  # 增加默认窗口大小
        self.root.resizable(True, True)
        
        # 初始化状态变量
        self.status_var = tk.StringVar(value="就绪...")
        
        # Variables
        self.is_recording = False
        self.is_playing = False
        self.actions = []
        self.execution_count = tk.IntVar(value=1)
        self.execution_speed = tk.IntVar(value=100)
        self.mouse_precision = tk.IntVar(value=200)
        self.optimize_path = tk.BooleanVar(value=False)
        self.record_keyboard = tk.BooleanVar(value=True)
        
        # 用于跟踪组合键的变量
        self.active_modifiers = set()
        self.modifier_keys = {
            'ctrl', 'alt', 'shift', 'cmd', 'command', 
            'win', 'meta', 'super', 'option', 'control'
        }
        
        # 热键设置 - 使用键名，而不是键对象
        self.hotkeys = {
            "start_record": {"key": "F6", "display": "F6", "description": "开始/暂停录制"},
            "start_playback": {"key": "F10", "display": "F10", "description": "开始/暂停执行"}
        }
        
        # 用于存储监听器的变量
        self.keyboard_listener = None
        self.mouse_listener = None
        self.record_start_time = 0
        self.global_hotkey_listener = None  # 新增全局热键监听器
        
        # 设置应用程序样式
        style = ttk.Style()
        style.theme_use('clam')  # 使用更现代的主题
        
        # 配置自定义样式
        style.configure('Main.TFrame', background=self.COLORS['bg'])
        style.configure('Settings.TLabelframe', background=self.COLORS['frame_bg'], padding=15)
        style.configure('Settings.TLabelframe.Label', 
                       font=('Microsoft YaHei UI', 10),
                       background=self.COLORS['frame_bg'],
                       foreground=self.COLORS['fg'])
        
        # 按钮样式
        style.configure('Action.TButton',
                       padding=10,
                       font=('Microsoft YaHei UI', 9),
                       background=self.COLORS['button'],
                       foreground=self.COLORS['fg'])
        style.map('Action.TButton',
                 background=[('pressed', self.COLORS['button_pressed']),
                           ('active', self.COLORS['button'])])
        
        # 录制按钮特殊样式
        style.configure('Record.TButton',
                       padding=10,
                       font=('Microsoft YaHei UI', 9, 'bold'),
                       background=self.COLORS['accent'],
                       foreground='white')
        style.map('Record.TButton',
                 background=[('pressed', '#2980b9'),
                           ('active', '#3498db')])
        
        # 树形列表样式
        style.configure('Tree.Treeview',
                       background=self.COLORS['frame_bg'],
                       foreground=self.COLORS['fg'],
                       fieldbackground=self.COLORS['frame_bg'],
                       rowheight=25,
                       font=('Microsoft YaHei UI', 9))
        style.configure('Tree.Treeview.Heading',
                       background=self.COLORS['button'],
                       font=('Microsoft YaHei UI', 9, 'bold'))
        style.map('Tree.Treeview',
                 background=[('selected', self.COLORS['tree_selected'])],
                 foreground=[('selected', self.COLORS['fg'])])
        
        # 标签和输入框样式
        style.configure('Status.TLabel',
                       font=('Microsoft YaHei UI', 9),
                       background=self.COLORS['bg'],
                       foreground=self.COLORS['fg'])
        style.configure('Title.TLabel',
                       font=('Microsoft YaHei UI', 12, 'bold'),
                       background=self.COLORS['bg'],
                       foreground=self.COLORS['fg'])
        
        # 设置根窗口背景色
        self.root.configure(bg=self.COLORS['bg'])
        
        # 尝试加载热键设置
        self.load_hotkeys()
        
        # Configure PyAutoGUI settings
        pyautogui.FAILSAFE = True
        
        # Create the UI
        self.create_ui()
        
        # 绑定热键
        self.apply_hotkey_bindings()
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 备用鼠标跟踪变量
        self.last_mouse_pos = (0, 0)
        self.mouse_track_running = False
        self.backup_recording = False

    def on_closing(self):
        """处理窗口关闭事件，确保监听器正确停止"""
        try:
            # 添加确认对话框，防止误触发
            if self.is_recording or self.is_playing:
                if not messagebox.askyesno("确认退出", "当前正在录制或播放，确定要退出吗？"):
                    return
            
            # 停止所有活动
            if self.is_recording:
                self.stop_recording()
            if self.is_playing:
                self.stop_playback()
            
            # 停止备用鼠标跟踪
            self.mouse_track_running = False
            
            # 停止所有监听器
            self.stop_all_listeners()
            
            # 关闭窗口
            self.root.destroy()
        except Exception as e:
            print(f"关闭程序时出错: {e}")
            # 确保程序能正确退出
            try:
                self.root.destroy()
            except:
                pass
    
    def stop_all_listeners(self):
        """安全地停止所有监听器"""
        try:
            if PYNPUT_AVAILABLE:
                # 停止全局热键监听器
                if hasattr(self, 'global_hotkey_listener') and self.global_hotkey_listener:
                    try:
                        self.global_hotkey_listener.stop()
                    except:
                        pass
                    self.global_hotkey_listener = None
                
                # 停止键盘监听器
                if hasattr(self, 'keyboard_listener') and self.keyboard_listener:
                    try:
                        self.keyboard_listener.stop()
                    except:
                        pass
                    self.keyboard_listener = None
                
                # 停止鼠标监听器
                if hasattr(self, 'mouse_listener') and self.mouse_listener:
                    try:
                        self.mouse_listener.stop()
                    except:
                        pass
                    self.mouse_listener = None
        except Exception as e:
            print(f"停止监听器时出错: {e}")

    def create_ui(self):
        # 创建状态栏
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 配置状态栏样式
        self.status_bar.configure(font=('Microsoft YaHei UI', 9),
                                bg=self.COLORS['frame_bg'],
                                fg=self.COLORS['fg'])
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10", style='Main.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建选项卡
        tab_control = ttk.Notebook(main_frame)
        
        # 主要标签页
        main_tab = ttk.Frame(tab_control, style='Main.TFrame')
        hotkeys_tab = ttk.Frame(tab_control, style='Main.TFrame')
        
        tab_control.add(main_tab, text="主界面")
        tab_control.add(hotkeys_tab, text="热键设置")
        
        tab_control.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ===== 主界面标签页 =====
        main_tab_frame = ttk.Frame(main_tab, padding="10", style='Main.TFrame')
        main_tab_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧配置框架
        settings_frame = ttk.LabelFrame(main_tab_frame, text="配置 (Settings)", 
                                      padding="15", style='Settings.TLabelframe')
        settings_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        
        # 执行次数
        ttk.Label(settings_frame, text="执行次数:", font=('Microsoft YaHei UI', 9)).grid(row=0, column=0, sticky=tk.W, pady=8)
        count_spin = ttk.Spinbox(settings_frame, from_=1, to=999, textvariable=self.execution_count, width=10)
        count_spin.grid(row=0, column=1, sticky=tk.W, pady=8, padx=5)
        
        # 鼠标精度
        ttk.Label(settings_frame, text="鼠标精度:", font=('Microsoft YaHei UI', 9)).grid(row=1, column=0, sticky=tk.W, pady=8)
        precision_spin = ttk.Spinbox(settings_frame, from_=1, to=1000, textvariable=self.mouse_precision, width=10)
        precision_spin.grid(row=1, column=1, sticky=tk.W, pady=8, padx=5)
        
        # 执行速度
        ttk.Label(settings_frame, text="执行速度%:", font=('Microsoft YaHei UI', 9)).grid(row=2, column=0, sticky=tk.W, pady=8)
        speed_spin = ttk.Spinbox(settings_frame, from_=1, to=200, textvariable=self.execution_speed, width=10)
        speed_spin.grid(row=2, column=1, sticky=tk.W, pady=8, padx=5)
        
        # 优化路径选项
        optimize_check = ttk.Checkbutton(settings_frame, text="优化鼠标路径", variable=self.optimize_path)
        optimize_check.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=8)
        
        # 记录键盘选项
        keyboard_check = ttk.Checkbutton(settings_frame, text="记录键盘输入", variable=self.record_keyboard)
        keyboard_check.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=8)
        
        # 热键显示
        ttk.Separator(settings_frame, orient=tk.HORIZONTAL).grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=15)
        
        ttk.Label(settings_frame, text="快捷键:", font=('Microsoft YaHei UI', 9, 'bold')).grid(row=6, column=0, sticky=tk.W, pady=8)
        hotkey_frame = ttk.Frame(settings_frame)
        hotkey_frame.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=8)
        
        ttk.Label(hotkey_frame, text=f"录制: {self.hotkeys['start_record']['display']}", 
                 font=('Microsoft YaHei UI', 9)).grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Label(hotkey_frame, text=f"播放: {self.hotkeys['start_playback']['display']}", 
                 font=('Microsoft YaHei UI', 9)).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # 右侧操作框架
        action_frame = ttk.Frame(main_tab_frame, style='Main.TFrame')
        action_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 操作按钮
        btn_frame = ttk.Frame(action_frame, style='Main.TFrame')
        btn_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.record_btn = ttk.Button(btn_frame, text="开始录制", command=self.toggle_recording,
                                   style='Record.TButton', width=15)
        self.record_btn.pack(side=tk.LEFT, padx=5)
        
        self.play_btn = ttk.Button(btn_frame, text="启动", command=self.start_playback,
                                 style='Action.TButton', width=15)
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="删除录制", command=self.clear_recording,
                                 style='Action.TButton', width=15)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.optimize_path_btn = ttk.Button(btn_frame, text="优化路径", command=self.optimize_recorded_path,
                                 style='Action.TButton', width=15)
        self.optimize_path_btn.pack(side=tk.LEFT, padx=5)
        
        self.compress_time_btn = ttk.Button(btn_frame, text="压缩时间", command=self.compress_action_time,
                                 style='Action.TButton', width=15)
        self.compress_time_btn.pack(side=tk.LEFT, padx=5)
        
        # 动作记录区域
        record_frame = ttk.LabelFrame(action_frame, text="动作记录", padding="10",
                                    style='Settings.TLabelframe')
        record_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview来显示动作记录
        columns = ('序号', '类型', '详情', '时间')
        self.action_tree = ttk.Treeview(record_frame, columns=columns, show='headings',
                                      style='Tree.Treeview', height=15)
        
        # 设置列标题和宽度
        self.action_tree.heading('序号', text='序号', anchor=tk.CENTER)
        self.action_tree.heading('类型', text='类型', anchor=tk.CENTER)
        self.action_tree.heading('详情', text='详情', anchor=tk.W)
        self.action_tree.heading('时间', text='时间', anchor=tk.CENTER)
        
        self.action_tree.column('序号', width=60, anchor=tk.CENTER)
        self.action_tree.column('类型', width=80, anchor=tk.CENTER)
        self.action_tree.column('详情', width=300, anchor=tk.W)
        self.action_tree.column('时间', width=80, anchor=tk.CENTER)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(record_frame, orient=tk.VERTICAL, command=self.action_tree.yview)
        self.action_tree.configure(yscrollcommand=scrollbar.set)
        
        # 打包组件
        self.action_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定右键菜单和快捷键
        self.action_tree.bind('<Button-3>', self.show_context_menu)
        self.action_tree.bind('<Delete>', lambda e: self.delete_selected_action())
        self.action_tree.bind('<Double-Button-1>', self.edit_selected_action)
        
        # 创建右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="编辑 (双击)", command=self.edit_selected_action)
        self.context_menu.add_command(label="删除 (Del)", command=self.delete_selected_action)
        
        # 添加编辑对话框
        self.edit_dialog = None
        
        # ===== 热键设置标签页 =====
        hotkeys_frame = ttk.Frame(hotkeys_tab, padding="15", style='Main.TFrame')
        hotkeys_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(hotkeys_frame, text="热键设置", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 15))
        
        # 创建热键设置区域
        for i, (action, data) in enumerate(self.hotkeys.items()):
            frame = ttk.Frame(hotkeys_frame)
            frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(frame, text=f"{data['description']}:").pack(side=tk.LEFT, padx=(0, 10))
            
            # 显示当前热键
            current_key_var = tk.StringVar(value=data['display'])
            current_key = ttk.Entry(frame, textvariable=current_key_var, width=10, state="readonly")
            current_key.pack(side=tk.LEFT, padx=(0, 10))
            
            # 设置热键按钮
            set_btn = ttk.Button(frame, text="设置热键", 
                               command=lambda a=action, v=current_key_var: self.set_hotkey(a, v))
            set_btn.pack(side=tk.LEFT)
        
        # 保存和重置按钮
        btn_frame = ttk.Frame(hotkeys_frame)
        btn_frame.pack(fill=tk.X, pady=10, side=tk.BOTTOM)
        
        ttk.Button(btn_frame, text="保存热键设置", command=self.save_hotkeys).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="重置为默认", command=self.reset_hotkeys).pack(side=tk.LEFT, padx=5)

        # 状态指示 - 显示pynput是否可用
        status_frame = ttk.Frame(hotkeys_frame)
        status_frame.pack(fill=tk.X, pady=10, side=tk.BOTTOM)
        
        status_text = "使用标准录制方式" if PYNPUT_AVAILABLE else "使用备用录制方式"
        status_color = "green" if PYNPUT_AVAILABLE else "orange"
        ttk.Label(status_frame, text=f"状态: {status_text}", foreground=status_color).pack(side=tk.LEFT)
     
    def apply_hotkey_bindings(self):
        # 清除旧绑定
        all_bindings = self.root.bind()
        for binding in all_bindings:
            if isinstance(binding, str) and binding.startswith("<Key"):
                try:
                    self.root.unbind(binding)
                except:
                    pass
        
        # 使用Tkinter内置的按键绑定
        self.root.bind("<KeyPress>", self.handle_key_press)
    
    def handle_key_press(self, event):
        """处理键盘按下事件"""
        key_pressed = event.keysym
        
        # 检查是否为录制热键
        if key_pressed.upper() == self.hotkeys["start_record"]["key"].upper():
            self.toggle_recording()
            return "break"
            
        # 检查是否为播放热键
        if key_pressed.upper() == self.hotkeys["start_playback"]["key"].upper():
            self.toggle_playback()
            return "break"
        
        return None
    
    def set_hotkey(self, action, display_var):
        """显示一个对话框让用户设置新的热键"""
        dialog = tk.Toplevel(self.root)
        dialog.title("设置热键")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="按下您想要设置的键...", font=("Arial", 10)).pack(pady=20)
        
        key_var = tk.StringVar(value="等待按键...")
        key_display = ttk.Label(dialog, textvariable=key_var, font=("Arial", 12, "bold"))
        key_display.pack(pady=10)
        
        # 使用Tkinter直接捕获按键
        def on_dialog_key_press(evt):
            key_name = evt.keysym
            
            key_var.set(key_name.upper())
            self.hotkeys[action]['key'] = key_name.upper()
            self.hotkeys[action]['display'] = key_name.upper()
            display_var.set(key_name.upper())
            
            dialog.after(100, dialog.destroy)
            return "break"  # 阻止事件进一步传播
        
        dialog.bind("<KeyPress>", on_dialog_key_press)
        
        # 取消按钮
        ttk.Button(dialog, text="取消", command=dialog.destroy).pack(pady=10)
    
    def save_hotkeys(self):
        """保存热键设置到配置文件"""
        try:
            with open('hotkeys.json', 'w') as f:
                json.dump(self.hotkeys, f)
            messagebox.showinfo("成功", "热键设置已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存热键设置失败: {str(e)}")
    
    def load_hotkeys(self):
        """从配置文件加载热键设置"""
        if os.path.exists('hotkeys.json'):
            try:
                with open('hotkeys.json', 'r') as f:
                    loaded_hotkeys = json.load(f)
                    self.hotkeys.update(loaded_hotkeys)
            except Exception:
                # 加载失败时使用默认热键
                pass
    
    def reset_hotkeys(self):
        """重置为默认热键设置"""
        self.hotkeys = {
            "start_record": {"key": "F6", "display": "F6", "description": "开始/暂停录制"},
            "start_playback": {"key": "F10", "display": "F10", "description": "开始/暂停执行"}
        }
        self.apply_hotkey_bindings()
        self.save_hotkeys()
        messagebox.showinfo("成功", "热键已重置为默认值")
        
        # 刷新界面中的热键显示
        self.root.after(100, self.refresh_ui)
    
    def refresh_ui(self):
        """刷新界面中的热键显示"""
        # 重新创建UI或更新热键显示部分
        self.create_ui()
    
    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        if self.is_playing:
            messagebox.showwarning("警告", "请先停止播放")
            return
            
        self.actions = []
        self.refresh_action_display()  # 清空显示
        self.is_recording = True
        self.record_btn.config(text="停止录制")
        self.status_var.set("正在录制...")
        
        # 记录开始时间
        self.record_start_time = time.time()
        
        # 选择适当的录制方法
        if PYNPUT_AVAILABLE:
            # 使用pynput方式录制
            self.start_pynput_recording()
            if self.record_keyboard.get():
                self.start_keyboard_recording()
            # 启动全局热键监听
            self.start_global_hotkeys()
        else:
            # 使用备用方式录制
            self.start_backup_recording()
    
    def start_pynput_recording(self):
        """使用pynput库录制鼠标动作"""
        try:
            # 确保没有活动的监听器
            self.stop_all_listeners()
            
            # 启动录制线程
            self.recording_thread = threading.Thread(target=self._record_mouse_events)
            self.recording_thread.daemon = True
            self.recording_thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"启动录制失败: {str(e)}")
            self.is_recording = False
            self.record_btn.config(text="开始录制")
            self.status_var.set("录制启动失败")
            
            # 尝试备用方法
            self.start_backup_recording()
    
    def start_backup_recording(self):
        """使用备用方法录制鼠标动作"""
        self.backup_recording = True
        self.mouse_track_running = True
        
        # 启动备用录制线程
        self.backup_thread = threading.Thread(target=self._backup_record_mouse)
        self.backup_thread.daemon = True
        self.backup_thread.start()
    
    def _backup_record_mouse(self):
        """备用鼠标录制方法 - 使用pyautogui而不是pynput"""
        start_time = self.record_start_time
        last_pos = pyautogui.position()
        last_time = time.time() - start_time
        
        # 添加初始位置
        self.actions.append({
            'type': 'move',
            'x': last_pos[0],
            'y': last_pos[1],
            'time': last_time
        })
        self.root.after(0, lambda: self.update_log(f"移动到: ({last_pos[0]}, {last_pos[1]})\n"))
        
        try:
            while self.mouse_track_running and self.is_recording:
                if not self.root.winfo_exists():
                    break
                    
                # 检查鼠标位置
                current_pos = pyautogui.position()
                current_time = time.time() - start_time
                
                # 检查位置是否变化
                precision = self.mouse_precision.get() / 10
                # 根据优化路径选项决定是否过滤移动事件
                if not self.optimize_path.get() or \
                   (abs(current_pos[0] - last_pos[0]) > precision or 
                    abs(current_pos[1] - last_pos[1]) > precision):
                    
                    # 记录移动
                    self.actions.append({
                        'type': 'move',
                        'x': current_pos[0],
                        'y': current_pos[1],
                        'time': current_time
                    })
                    self.root.after(0, lambda x=current_pos[0], y=current_pos[1]: 
                                   self.update_log(f"移动到: ({x}, {y})\n"))
                    last_pos = current_pos
                
                # 检查鼠标点击 - 无法直接检测，需要用户手动点击录制界面上的"标记点击"按钮
                
                # 短暂睡眠以减少CPU使用
                time.sleep(0.01)
                
        except Exception as e:
            print(f"备用录制出错: {e}")
        finally:
            self.mouse_track_running = False
    
    def _record_mouse_events(self):
        """使用pynput录制鼠标事件"""
        start_time = self.record_start_time
        mouse_listener = None
        last_x = last_y = None
        last_record_time = None
        last_move_time = None
        
        def should_record_point(x, y, current_time):
            """判断是否需要记录该点"""
            nonlocal last_x, last_y, last_record_time, last_move_time
            
            # 防止传入None值
            if x is None or y is None or current_time is None:
                return False
                
            if last_x is None or last_y is None:
                return True  # 记录起点
                
            # 计算移动距离
            try:
                distance = ((x - last_x) ** 2 + (y - last_y) ** 2) ** 0.5
                min_distance = max(1, self.mouse_precision.get() / 5)  # 最小移动距离，确保至少为1像素
            except (TypeError, ValueError):
                print("计算距离出错，使用默认值")
                distance = 0
                min_distance = 5
            
            if not self.optimize_path.get():
                # 不优化路径时，按照精度记录点
                return distance > min_distance
            
            # 优化路径模式下的记录逻辑
            if last_move_time is None:
                last_move_time = current_time
            
            # 检查是否停留超过1秒
            try:
                if distance < min_distance and (current_time - last_move_time) > 1.0:
                    last_move_time = current_time
                    return True
            except TypeError:
                last_move_time = current_time
            
            # 如果发生移动，更新last_move_time
            if distance > min_distance:
                last_move_time = current_time
            
            # 只在开始新的移动序列时记录点
            try:
                if last_record_time is None or (current_time - last_record_time) > 0.1:
                    return distance > min_distance
            except TypeError:
                last_record_time = current_time
                return True
            
            return False
        
        def on_move(x, y):
            nonlocal last_x, last_y, last_record_time
            
            if not self.is_recording:
                return False
                
            try:
                # 防止None值处理
                if x is None or y is None:
                    return True
                    
                current_time = time.time() - start_time
                
                if should_record_point(x, y, current_time):
                    # 确保值是整数
                    x_int = int(round(x))
                    y_int = int(round(y))
                    
                    self.actions.append({
                        'type': 'move',
                        'x': x_int,
                        'y': y_int,
                        'time': current_time
                    })
                    last_x, last_y = x_int, y_int
                    last_record_time = current_time
                    
                    # 使用after方法安全地更新UI
                    if self.root.winfo_exists():
                        self.root.after(0, lambda: self.update_log(f"移动到: ({x_int}, {y_int})\n"))
            except Exception as e:
                print(f"记录移动时出错: {e}")
                return False
        
        def on_click(x, y, button, pressed):
            if not self.is_recording:
                return False
                
            try:
                # 防止None值处理
                if x is None or y is None or button is None:
                    return True
                    
                current_time = time.time() - start_time
                
                # 转换按钮名称为字符串
                if button == mouse.Button.left:
                    button_name = 'left'
                elif button == mouse.Button.right:
                    button_name = 'right'
                elif button == mouse.Button.middle:
                    button_name = 'middle'
                else:
                    # 处理其他可能的按钮
                    try:
                        button_name = button.name
                    except:
                        button_name = 'left'  # 默认为左键
                
                # 确保值是整数
                x_int = int(round(x))
                y_int = int(round(y))
                
                self.actions.append({
                    'type': 'click',
                    'x': x_int,
                    'y': y_int,
                    'button': button_name,
                    'pressed': pressed,
                    'time': current_time
                })
                
                if self.root.winfo_exists():
                    self.root.after(0, lambda: self.update_log(f"点击 {button_name}: ({x_int}, {y_int})\n"))
            except Exception as e:
                print(f"记录点击时出错: {e}")
                return False
        
        try:
            # 启动鼠标监听器
            self.mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click)
            self.mouse_listener.start()
            
            # 持续检查录制状态
            while self.is_recording:
                time.sleep(0.01)
                if not self.root.winfo_exists():
                    break
        except Exception as e:
            print(f"录制过程出错: {e}")
            # 尝试备用方法
            if not self.backup_recording and self.is_recording:
                self.start_backup_recording()
        finally:
            # 确保监听器被正确停止
            try:
                if self.mouse_listener and hasattr(self.mouse_listener, 'stop'):
                    self.mouse_listener.stop()
                self.mouse_listener = None
            except:
                pass
    
    def update_log(self, text):
        """更新动作记录显示"""
        self.refresh_action_display()
    
    def stop_recording(self):
        self.is_recording = False
        self.mouse_track_running = False
        self.backup_recording = False
        
        # 停止所有监听器
        self.stop_all_listeners()
        
        self.record_btn.config(text="开始录制")
        self.status_var.set(f"录制完成, 共 {len(self.actions)} 个动作")
        
    def toggle_playback(self):
        if self.is_playing:
            self.stop_playback()
        else:
            self.start_playback()
    
    def start_playback(self):
        if self.is_recording:
            messagebox.showwarning("警告", "请先停止录制")
            return
            
        if not self.actions:
            messagebox.showinfo("提示", "没有录制的动作")
            return
            
        self.is_playing = True
        self.play_btn.config(text="停止")
        
        # Start playback in a separate thread
        self.playback_thread = threading.Thread(target=self._playback_actions)
        self.playback_thread.daemon = True
        self.playback_thread.start()
    
    def _playback_actions(self):
        """回放录制的动作"""
        try:
            count = self.execution_count.get()
            speed_factor = self.execution_speed.get() / 100.0
            last_mouse_pos = pyautogui.position()
            check_interval = 0.1  # 检查用户干预的时间间隔
            
            for i in range(count):
                if not self.is_playing:
                    break
                    
                self.status_var.set(f"正在执行第 {i+1}/{count} 次")
                
                last_time = 0
                last_check_time = time.time()
                
                # 跟踪当前按下的所有键
                pressed_keys = set()  # 所有当前按下的键
                active_modifiers = set()  # 活动修饰键（仅限修饰键）
                
                for action in self.actions:
                    if not self.is_playing:
                        break
                    
                    current_time = action['time']
                    current_real_time = time.time()
                    
                    # 定期检查用户是否移动了鼠标
                    if current_real_time - last_check_time >= check_interval:
                        current_pos = pyautogui.position()
                        if current_pos != last_mouse_pos:
                            print("检测到用户鼠标移动，停止播放")
                            self.stop_playback()
                            return
                        last_mouse_pos = current_pos
                        last_check_time = current_real_time
                    
                    # 优化加速逻辑，使加速效果更明显
                    if speed_factor > 0:
                        # 原始等待时间
                        original_wait = current_time - last_time
                        
                        # 新的加速算法，使高速时更明显
                        if speed_factor <= 1:
                            # 低速模式 (1-100%)
                            wait_time = original_wait / speed_factor
                        else:
                            # 高速模式 (>100%)
                            # 使用指数衰减来使高速更明显
                            wait_time = original_wait / (speed_factor ** 1.5)
                        
                        # 限制最小等待时间，避免过快导致无法执行
                        if wait_time > 0.0001:  # 0.1毫秒的最小延迟
                            time.sleep(wait_time)
                    
                    # 执行动作
                    try:
                        if action['type'] == 'move':
                            # 直接移动到目标位置，不使用动画
                            pyautogui.moveTo(action['x'], action['y'], duration=0)
                            last_mouse_pos = (action['x'], action['y'])
                        elif action['type'] == 'click':
                            button = action.get('button', 'left')
                            pyautogui.click(action['x'], action['y'], button=button)
                            last_mouse_pos = (action['x'], action['y'])
                        elif action['type'] == 'key':
                            key_value = action.get('key')
                            if key_value is None:
                                print("警告: 键值为None，跳过此操作")
                                continue
                            
                            # 对空格键的特殊处理
                            if key_value.lower() in ['blank', 'space', 'spacebar', ' ']:
                                key_value = 'space'  # 使用PyAutoGUI能识别的名称
                                print("处理空格键")
                            
                            # 处理特殊情况如"ctrl l"（左ctrl）
                            elif key_value == "ctrl l" or key_value == "ctrl_l":
                                key_value = "ctrl"
                            elif key_value == "ctrl r" or key_value == "ctrl_r":
                                key_value = "ctrl"
                            elif key_value == "shift l" or key_value == "shift_l":
                                key_value = "shift"
                            elif key_value == "shift r" or key_value == "shift_r":
                                key_value = "shift"
                            elif key_value == "alt l" or key_value == "alt_l":
                                key_value = "alt"
                            elif key_value == "alt r" or key_value == "alt_r":
                                key_value = "alt"
                            
                            # 判断是否是修饰键
                            is_modifier = key_value.lower() in self.modifier_keys
                            
                            # 已有显式的修饰键信息
                            modifiers = action.get('modifiers', [])
                            
                            key_action = action.get('action')
                            if key_action == 'press':
                                # 先处理显式的修饰键
                                for mod in modifiers:
                                    if mod not in active_modifiers:
                                        pyautogui.keyDown(mod)
                                        active_modifiers.add(mod)
                                        pressed_keys.add(mod)
                                
                                # 对于连续按键操作，检查当前是否有修饰键被按下但未释放
                                # (这处理现有录制的连续按键情况)
                                for key in pressed_keys:
                                    if key.lower() in self.modifier_keys:
                                        active_modifiers.add(key.lower())
                                
                                # 按下当前键
                                print(f"按下键: {key_value}")
                                if active_modifiers:
                                    print(f"使用组合键: {'+'.join(active_modifiers)}+{key_value}")
                                
                                # 为空格键增加额外重试逻辑
                                success = False
                                retry_count = 0
                                max_retries = 3
                                
                                while not success and retry_count < max_retries:
                                    try:
                                        pyautogui.keyDown(key_value)
                                        success = True
                                    except Exception as e:
                                        print(f"按键失败: {e}, 重试中... ({retry_count+1}/{max_retries})")
                                        retry_count += 1
                                        if key_value == 'space' and retry_count == max_retries - 1:
                                            # 最后一次尝试用不同的方式发送空格
                                            print("尝试替代方法发送空格")
                                            pyautogui.press('space')
                                            success = True
                                        time.sleep(0.1)  # 等待一会再重试
                                
                                if success:
                                    pressed_keys.add(key_value)
                                    # 如果是修饰键，添加到修饰键集合
                                    if is_modifier:
                                        active_modifiers.add(key_value.lower())
                                else:
                                    print(f"无法按下键: {key_value}")
                                
                            elif key_action == 'release':
                                # 释放当前键
                                print(f"释放键: {key_value}")
                                try:
                                    pyautogui.keyUp(key_value)
                                except Exception as e:
                                    print(f"释放键失败: {e}")
                                    # 对空格键的特殊处理
                                    if key_value == 'space':
                                        try:
                                            # 尝试其他方法释放空格键
                                            print("尝试替代方法释放空格")
                                            pyautogui.press('space')
                                        except:
                                            pass
                                
                                # 从已按下键集合中移除
                                if key_value in pressed_keys:
                                    pressed_keys.remove(key_value)
                                
                                # 如果是修饰键，从修饰键集合中移除
                                if key_value.lower() in active_modifiers:
                                    active_modifiers.remove(key_value.lower())
                    except Exception as e:
                        print(f"执行动作时出错: {e}")
                    
                    last_time = current_time
                
                # 确保所有键都被释放，避免按键卡住
                for key in list(pressed_keys):
                    try:
                        print(f"释放剩余的键: {key}")
                        pyautogui.keyUp(key)
                    except Exception as e:
                        print(f"释放键时出错: {e}")
                        # 对空格键的特殊处理
                        if key == 'space':
                            try:
                                print("尝试替代方法释放空格")
                                pyautogui.press('space')
                            except:
                                pass
                pressed_keys.clear()
                active_modifiers.clear()
                
                # 每次执行完一轮后的短暂暂停，根据速度因子调整
                if i < count - 1:
                    # 优化轮次间的等待时间
                    if speed_factor <= 1:
                        pause_time = 0.2 / speed_factor
                    else:
                        pause_time = 0.2 / (speed_factor ** 1.5)
                    time.sleep(max(0.01, pause_time))  # 确保最小暂停时间
                    
        except Exception as e:
            print(f"回放过程出错: {e}")
        finally:
            self.is_playing = False
            if self.root.winfo_exists():
                self.root.after(0, lambda: self.play_btn.config(text="启动"))
                self.root.after(0, lambda: self.status_var.set("就绪..."))
    
    def stop_playback(self):
        self.is_playing = False
        self.play_btn.config(text="启动")
        self.status_var.set("就绪...")
    
    def clear_recording(self):
        if self.is_recording or self.is_playing:
            messagebox.showwarning("警告", "请先停止录制和播放")
            return
            
        self.actions = []
        self.refresh_action_display()  # 清空显示
        self.status_var.set("录制已清除")
    
    def save_recording(self, filename="mouse_actions.json"):
        if not self.actions:
            messagebox.showinfo("提示", "没有录制的动作可保存")
            return
            
        try:
            with open(filename, 'w') as f:
                json.dump(self.actions, f)
            self.status_var.set(f"录制已保存到 {filename}")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def load_recording(self, filename="mouse_actions.json"):
        if not os.path.exists(filename):
            messagebox.showinfo("提示", f"找不到文件 {filename}")
            return
            
        try:
            with open(filename, 'r') as f:
                self.actions = json.load(f)
            
            self.refresh_action_display()  # 清空显示
            self.status_var.set(f"已加载 {len(self.actions)} 个动作")
        except Exception as e:
            messagebox.showerror("错误", f"加载失败: {str(e)}")

    def start_keyboard_recording(self):
        """开始录制键盘事件"""
        if not PYNPUT_AVAILABLE:
            messagebox.showerror("错误", "无法录制键盘，未安装pynput库")
            return
            
        # 重置活动修饰键集合
        self.active_modifiers = set()
            
        def on_press(key):
            try:
                if not self.is_recording:
                    return False
                    
                # 处理key可能是None的情况
                if key is None:
                    print("警告: 接收到None键值")
                    return True
                    
                current_time = time.time() - self.record_start_time
                
                # 处理特殊键和普通键
                key_str = None
                try:
                    # 尝试获取字符
                    key_str = key.char
                except AttributeError:
                    # 特殊键处理
                    key_str = str(key).replace('Key.', '')
                    
                # 确保key_str不为None
                if key_str is None:
                    key_str = "unknown"
                
                # 标准化空格键表示
                if key_str.lower() in ['blank', 'space', 'spacebar', ' ']:
                    key_str = 'space'
                    print("记录空格键")
                
                # 检查是否是修饰键
                is_modifier = False
                key_lower = key_str.lower()
                if key_lower in self.modifier_keys:
                    is_modifier = True
                    self.active_modifiers.add(key_lower)
                
                # 创建动作对象，包含修饰键信息
                action_data = {
                    'type': 'key',
                    'key': key_str,
                    'action': 'press',
                    'time': current_time,
                    'is_modifier': is_modifier
                }
                
                # 如果有活动修饰键且当前按键不是修饰键，记录组合键信息
                if self.active_modifiers and not is_modifier:
                    action_data['modifiers'] = list(self.active_modifiers)
                    # 在UI中显示组合键
                    combo_str = '+'.join(m.capitalize() for m in self.active_modifiers) + "+" + key_str
                    if self.root.winfo_exists():
                        self.root.after(0, lambda: self.update_log(f"组合键: {combo_str}\n"))
                else:
                    # 使用after方法安全地更新UI
                    if self.root.winfo_exists():
                        self.root.after(0, lambda: self.update_log(f"按下键: {key_str}\n"))
                
                self.actions.append(action_data)
                return True
            except Exception as e:
                print(f"处理按键按下事件出错: {e}")
                return True
                
        def on_release(key):
            try:
                if not self.is_recording:
                    return False
                    
                # 处理key可能是None的情况
                if key is None:
                    return True
                    
                current_time = time.time() - self.record_start_time
                
                # 处理特殊键和普通键
                key_str = None
                try:
                    # 尝试获取字符
                    key_str = key.char
                except AttributeError:
                    # 特殊键处理
                    key_str = str(key).replace('Key.', '')
                    
                # 确保key_str不为None
                if key_str is None:
                    key_str = "unknown"
                
                # 标准化空格键表示
                if key_str.lower() in ['blank', 'space', 'spacebar', ' ']:
                    key_str = 'space'
                
                # 检查是否是修饰键
                key_lower = key_str.lower()
                if key_lower in self.modifier_keys:
                    # 从活动修饰键集合中移除
                    self.active_modifiers.discard(key_lower)
                
                self.actions.append({
                    'type': 'key',
                    'key': key_str,
                    'action': 'release',
                    'time': current_time
                })
                
                # 使用after方法安全地更新UI
                if self.root.winfo_exists():
                    self.root.after(0, lambda: self.update_log(f"释放键: {key_str}\n"))
                
                return True
            except Exception as e:
                print(f"处理按键释放事件出错: {e}")
                return True
        
        try:
            # 确保正确引用keyboard模块
            if hasattr(keyboard, 'Listener'):
                self.keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
                self.keyboard_listener.daemon = True
                self.keyboard_listener.start()
            else:
                print("警告: keyboard.Listener不可用")
        except Exception as e:
            print(f"启动键盘监听时出错: {e}")

    def show_context_menu(self, event):
        """显示右键菜单"""
        try:
            item = self.action_tree.identify_row(event.y)
            if item:
                self.action_tree.selection_set(item)
                self.context_menu.post(event.x_root, event.y_root)
        except:
            pass

    def delete_selected_action(self):
        """删除选中的动作"""
        try:
            selected_items = self.action_tree.selection()
            if not selected_items:
                return
                
            # 获取选中项的索引
            for item in selected_items:
                index = int(self.action_tree.item(item)['values'][0]) - 1
                if 0 <= index < len(self.actions):
                    self.actions.pop(index)
            
            # 重新显示所有动作
            self.refresh_action_display()
        except Exception as e:
            print(f"删除动作时出错: {e}")

    def refresh_action_display(self):
        """刷新动作显示"""
        # 清除现有显示
        for item in self.action_tree.get_children():
            self.action_tree.delete(item)
        
        # 重新显示所有动作
        for i, action in enumerate(self.actions):
            values = [i + 1]  # 序号
            
            if action['type'] == 'move':
                values.extend(['移动', f'({action["x"]}, {action["y"]})', f'{action["time"]:.2f}s'])
            elif action['type'] == 'click':
                values.extend(['点击', f'{action["button"]}: ({action["x"]}, {action["y"]})', f'{action["time"]:.2f}s'])
            elif action['type'] == 'key':
                # 改进键盘动作显示，添加组合键信息
                key_desc = action['key']
                if 'modifiers' in action and action['modifiers']:
                    mod_str = '+'.join(m.capitalize() for m in action['modifiers'])
                    key_desc = f"{mod_str}+{key_desc}"
                values.extend(['键盘', f'{action["action"]}: {key_desc}', f'{action["time"]:.2f}s'])
            
            self.action_tree.insert('', 'end', values=values)

    def start_global_hotkeys(self):
        """启动全局热键监听器"""
        if not PYNPUT_AVAILABLE:
            return
            
        def on_press(key):
            try:
                # 防止key为None
                if key is None:
                    return True
                    
                # 获取热键字符串
                key_str = None
                try:
                    # 尝试获取字符
                    key_str = key.char
                except AttributeError:
                    # 特殊键处理
                    key_str = str(key).replace('Key.', '')
                
                # 确保key_str不为None
                if key_str is None:
                    return True
                    
                # 将key_str转为大写以匹配热键设置
                key_str = key_str.upper()
                    
                # 检查是否匹配录制/播放热键
                record_hotkey = self.hotkeys.get("start_record", {}).get("key", "F6")
                play_hotkey = self.hotkeys.get("start_playback", {}).get("key", "F10")
                
                if key_str == record_hotkey:
                    # 在主线程中执行UI操作
                    if self.root.winfo_exists():
                        self.root.after(0, self.toggle_recording)
                        
                elif key_str == play_hotkey:
                    # 在主线程中执行UI操作
                    if self.root.winfo_exists():
                        self.root.after(0, self.toggle_playback)
                
                return True
            except Exception as e:
                print(f"处理全局热键时出错: {e}")
                return True
                
        # 启动监听器
        try:
            # 确保正确引用keyboard模块
            if hasattr(keyboard, 'Listener'):
                self.global_hotkey_listener = keyboard.Listener(on_press=on_press)
                self.global_hotkey_listener.daemon = True
                self.global_hotkey_listener.start()
            else:
                print("警告: keyboard.Listener不可用")
        except Exception as e:
            print(f"启动全局热键监听器时出错: {e}")

    def edit_selected_action(self, event=None):
        """编辑选中的动作"""
        try:
            selected_items = self.action_tree.selection()
            if not selected_items:
                return
                
            item = selected_items[0]  # 只编辑第一个选中项
            index = int(self.action_tree.item(item)['values'][0]) - 1
            if 0 <= index < len(self.actions):
                action = self.actions[index]
                self.show_edit_dialog(index, action)
        except Exception as e:
            print(f"编辑动作时出错: {e}")

    def show_edit_dialog(self, index, action):
        """显示编辑对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("编辑动作")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.COLORS['bg'])  # 设置对话框背景色
        
        # 设置对话框样式
        style = ttk.Style()
        style.configure('Dialog.TFrame',
                       padding=15,
                       background=self.COLORS['bg'])
        style.configure('Dialog.TLabel',
                       font=('Microsoft YaHei UI', 9),
                       background=self.COLORS['bg'],
                       foreground=self.COLORS['fg'])
        style.configure('Dialog.TButton',
                       padding=10,
                       font=('Microsoft YaHei UI', 9))
        
        # 创建编辑框架
        frame = ttk.Frame(dialog, style='Dialog.TFrame')
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 根据动作类型创建不同的编辑界面
        if action['type'] in ['move', 'click']:
            # 坐标编辑
            ttk.Label(frame, text="X坐标:", style='Dialog.TLabel').grid(row=0, column=0, sticky=tk.W, pady=8)
            x_var = tk.StringVar(value=str(action['x']))
            x_entry = ttk.Entry(frame, textvariable=x_var, width=15)
            x_entry.grid(row=0, column=1, padx=5, pady=8)
            
            ttk.Label(frame, text="Y坐标:", style='Dialog.TLabel').grid(row=1, column=0, sticky=tk.W, pady=8)
            y_var = tk.StringVar(value=str(action['y']))
            y_entry = ttk.Entry(frame, textvariable=y_var, width=15)
            y_entry.grid(row=1, column=1, padx=5, pady=8)
            
            if action['type'] == 'click':
                ttk.Label(frame, text="按键:", style='Dialog.TLabel').grid(row=2, column=0, sticky=tk.W, pady=8)
                button_var = tk.StringVar(value=action['button'])
                button_combo = ttk.Combobox(frame, textvariable=button_var, values=['left', 'right'], width=12)
                button_combo.grid(row=2, column=1, padx=5, pady=8)
        
        elif action['type'] == 'key':
            ttk.Label(frame, text="按键:", style='Dialog.TLabel').grid(row=0, column=0, sticky=tk.W, pady=8)
            key_var = tk.StringVar(value=action['key'])
            key_entry = ttk.Entry(frame, textvariable=key_var, width=15)
            key_entry.grid(row=0, column=1, padx=5, pady=8)
            
            ttk.Label(frame, text="动作:", style='Dialog.TLabel').grid(row=1, column=0, sticky=tk.W, pady=8)
            action_var = tk.StringVar(value=action['action'])
            action_combo = ttk.Combobox(frame, textvariable=action_var, values=['press', 'release'], width=12)
            action_combo.grid(row=1, column=1, padx=5, pady=8)
        
        # 时间编辑
        ttk.Label(frame, text="时间(秒):", style='Dialog.TLabel').grid(row=3, column=0, sticky=tk.W, pady=8)
        time_var = tk.StringVar(value=f"{action['time']:.2f}")
        time_entry = ttk.Entry(frame, textvariable=time_var, width=15)
        time_entry.grid(row=3, column=1, padx=5, pady=8)
        
        # 保存按钮
        def save_changes():
            try:
                # 更新动作数据
                if action['type'] in ['move', 'click']:
                    action['x'] = int(x_var.get())
                    action['y'] = int(y_var.get())
                    if action['type'] == 'click':
                        action['button'] = button_var.get()
                elif action['type'] == 'key':
                    action['key'] = key_var.get()
                    action['action'] = action_var.get()
                
                action['time'] = float(time_var.get())
                self.actions[index] = action
                self.refresh_action_display()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {str(e)}")
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=15)
        
        ttk.Button(btn_frame, text="保存", command=save_changes, style='Dialog.TButton', width=15).pack()

    def optimize_recorded_path(self):
        """优化已录制的路径，删除不必要的中间移动点"""
        if not self.actions:
            messagebox.showinfo("提示", "没有录制的动作可以优化")
            return
            
        optimized_actions = []
        last_move = None
        last_non_move = None
        
        for action in self.actions:
            if action['type'] == 'move':
                # 只保留最后一个移动点
                last_move = action
            else:
                # 如果有待处理的移动点，且上一个动作不是移动
                if last_move and (not last_non_move or last_non_move['time'] != last_move['time']):
                    optimized_actions.append(last_move)
                optimized_actions.append(action)
                last_non_move = action
                last_move = None
        
        # 如果最后一个动作是移动，需要添加
        if last_move:
            optimized_actions.append(last_move)
        
        self.actions = optimized_actions
        self.refresh_action_display()
        self.status_var.set(f"路径已优化，剩余 {len(self.actions)} 个动作")

    def compress_action_time(self):
        """压缩动作时间间隔"""
        if not self.actions:
            messagebox.showinfo("提示", "没有录制的动作可以压缩")
            return
            
        MIN_INTERVAL = 0.001  # 最小时间间隔（1毫秒）
        CLICK_INTERVAL = 0.01  # 点击操作的时间间隔（10毫秒）
        KEY_INTERVAL = 0.005   # 键盘操作的时间间隔（5毫秒）
        
        new_time = 0
        last_type = None
        
        for action in self.actions:
            if action is None:
                continue
                
            current_type = action.get('type')
            if current_type is None:
                continue
                
            # 根据动作类型设置不同的间隔
            if current_type == 'move':
                # 移动点增加最小间隔
                new_time += MIN_INTERVAL
            elif current_type == 'click':
                # 点击操作增加更大间隔
                new_time += CLICK_INTERVAL
            elif current_type == 'key':
                # 如果是连续的键盘输入，使用较小间隔
                if last_type == 'key':
                    new_time += MIN_INTERVAL
                else:
                    new_time += KEY_INTERVAL
                    
            action['time'] = new_time
            last_type = current_type
        
        self.refresh_action_display()
        self.status_var.set(f"时间已压缩，总时长: {new_time:.3f}秒")

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = MouseSpirit(root)
        root.mainloop()
    except Exception as e:
        print(f"程序运行时出错: {e}")
        # 显示错误对话框
        try:
            import tkinter.messagebox
            tkinter.messagebox.showerror("错误", f"程序运行时出错: {e}")
        except:
            pass 