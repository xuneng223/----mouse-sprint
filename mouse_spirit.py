import tkinter as tk
from tkinter import ttk, messagebox
import pyautogui
import time
import json
import os
import threading
import sys

# 尝试导入pynput，如果失败则使用备用方案
try:
    from pynput import mouse
    from pynput.keyboard import Key, KeyCode
    PYNPUT_AVAILABLE = True
except (ImportError, TypeError, AttributeError) as e:
    print(f"警告: pynput导入失败: {e}")
    print("将使用备用方法进行鼠标跟踪")
    PYNPUT_AVAILABLE = False

class MouseSpirit:
    def __init__(self, root):
        self.root = root
        self.root.title("鼠标精灵 (Mouse Spirit)")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        
        # Variables
        self.is_recording = False
        self.is_playing = False
        self.actions = []
        self.execution_count = tk.IntVar(value=1)
        self.execution_speed = tk.IntVar(value=100)
        self.mouse_precision = tk.IntVar(value=200)
        
        # 热键设置 - 使用键名，而不是键对象
        self.hotkeys = {
            "start_record": {"key": "F6", "display": "F6", "description": "开始/暂停录制"},
            "start_playback": {"key": "F10", "display": "F10", "description": "开始/暂停执行"}
        }
        
        # 用于存储监听器的变量
        self.keyboard_listener = None
        self.mouse_listener = None
        self.record_start_time = 0
        
        # 尝试加载热键设置
        self.load_hotkeys()
        
        # Configure PyAutoGUI settings
        pyautogui.FAILSAFE = True
        
        # Create the UI
        self.create_ui()
        
        # Status bar
        self.status_var = tk.StringVar(value="就绪...")
        self.status_bar = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
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
    
    def stop_all_listeners(self):
        """安全地停止所有监听器"""
        try:
            if PYNPUT_AVAILABLE:
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
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建选项卡
        tab_control = ttk.Notebook(main_frame)
        
        # 主要标签页
        main_tab = ttk.Frame(tab_control)
        hotkeys_tab = ttk.Frame(tab_control)
        
        tab_control.add(main_tab, text="主界面")
        tab_control.add(hotkeys_tab, text="热键设置")
        
        tab_control.pack(fill=tk.BOTH, expand=True)
        
        # ===== 主界面标签页 =====
        main_tab_frame = ttk.Frame(main_tab, padding="10")
        main_tab_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧配置框架
        settings_frame = ttk.LabelFrame(main_tab_frame, text="配置 (Settings)", padding="10")
        settings_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 执行次数
        ttk.Label(settings_frame, text="执行次数:").grid(row=0, column=0, sticky=tk.W, pady=5)
        count_spin = ttk.Spinbox(settings_frame, from_=1, to=999, textvariable=self.execution_count, width=10)
        count_spin.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # 鼠标精度
        ttk.Label(settings_frame, text="鼠标精度:").grid(row=1, column=0, sticky=tk.W, pady=5)
        precision_spin = ttk.Spinbox(settings_frame, from_=1, to=1000, textvariable=self.mouse_precision, width=10)
        precision_spin.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 执行速度
        ttk.Label(settings_frame, text="执行速度%:").grid(row=2, column=0, sticky=tk.W, pady=5)
        speed_spin = ttk.Spinbox(settings_frame, from_=1, to=200, textvariable=self.execution_speed, width=10)
        speed_spin.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 热键显示
        ttk.Separator(settings_frame, orient=tk.HORIZONTAL).grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        ttk.Label(settings_frame, text="快捷键:").grid(row=4, column=0, sticky=tk.W, pady=5)
        hotkey_frame = ttk.Frame(settings_frame)
        hotkey_frame.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Label(hotkey_frame, text=f"录制: {self.hotkeys['start_record']['display']}").grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Label(hotkey_frame, text=f"播放: {self.hotkeys['start_playback']['display']}").grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # 右侧操作框架
        action_frame = ttk.Frame(main_tab_frame)
        action_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # 操作按钮
        btn_frame = ttk.Frame(action_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.record_btn = ttk.Button(btn_frame, text="开始录制", command=self.toggle_recording)
        self.record_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.play_btn = ttk.Button(btn_frame, text="启动", command=self.start_playback)
        self.play_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.stop_btn = ttk.Button(btn_frame, text="删除录制", command=self.clear_recording)
        self.stop_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # 动作记录区域
        ttk.Label(action_frame, text="动作记录:").pack(anchor=tk.W)
        
        log_frame = ttk.Frame(action_frame, borderwidth=1, relief=tk.SUNKEN)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_frame, height=10, width=30, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        
        # ===== 热键设置标签页 =====
        hotkeys_frame = ttk.Frame(hotkeys_tab, padding="10")
        hotkeys_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(hotkeys_frame, text="热键设置", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
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
        self.log_text.delete(1.0, tk.END)
        self.is_recording = True
        self.record_btn.config(text="停止录制")
        self.status_var.set("正在录制...")
        
        # 记录开始时间
        self.record_start_time = time.time()
        
        # 选择适当的录制方法
        if PYNPUT_AVAILABLE:
            # 使用pynput方式录制
            self.start_pynput_recording()
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
                if (abs(current_pos[0] - last_pos[0]) > precision or 
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
        
        def on_move(x, y):
            if not self.is_recording:
                return False
            # 只记录达到精度要求的移动，避免太多事件
            precision = self.mouse_precision.get()
            if len(self.actions) == 0 or self.actions[-1]['type'] != 'move' or \
               (abs(self.actions[-1]['x'] - x) > precision/10 or abs(self.actions[-1]['y'] - y) > precision/10):
                try:
                    current_time = time.time() - start_time
                    self.actions.append({
                        'type': 'move',
                        'x': x,
                        'y': y,
                        'time': current_time
                    })
                    # 使用after方法安全地更新UI
                    if self.root.winfo_exists():
                        self.root.after(0, lambda: self.update_log(f"移动到: ({x}, {y})\n"))
                except Exception as e:
                    print(f"记录移动时出错: {e}")
                    return False
        
        def on_click(x, y, button, pressed):
            if not self.is_recording:
                return False
            try:
                if pressed:
                    current_time = time.time() - start_time
                    btn = 'left'
                    try:
                        if hasattr(button, 'name'):
                            btn = 'right' if button.name == 'right' else 'left'
                        elif str(button).endswith('.right'):
                            btn = 'right'
                    except:
                        pass
                        
                    self.actions.append({
                        'type': 'click',
                        'x': x,
                        'y': y,
                        'button': btn,
                        'time': current_time
                    })
                    # 使用after方法安全地更新UI
                    if self.root.winfo_exists():
                        self.root.after(0, lambda: self.update_log(f"点击 {btn}: ({x}, {y})\n"))
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
        """安全地更新日志文本"""
        try:
            if self.root.winfo_exists():
                self.log_text.insert(tk.END, text)
                self.log_text.see(tk.END)
        except Exception as e:
            print(f"更新日志时出错: {e}")
    
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
            
            for i in range(count):
                if not self.is_playing:
                    break
                    
                self.status_var.set(f"正在执行第 {i+1}/{count} 次")
                
                last_time = 0
                for action in self.actions:
                    if not self.is_playing:
                        break
                        
                    # 等待适当的时间，根据速度调整
                    if speed_factor > 0:
                        sleep_time = (action['time'] - last_time) / speed_factor
                        if sleep_time > 0:
                            time.sleep(sleep_time)
                    
                    # 执行动作
                    try:
                        if action['type'] == 'move':
                            pyautogui.moveTo(action['x'], action['y'])
                        elif action['type'] == 'click':
                            button = action.get('button', 'left')
                            pyautogui.click(action['x'], action['y'], button=button)
                    except Exception as e:
                        print(f"执行动作时出错: {e}")
                    
                    last_time = action['time']
        except Exception as e:
            print(f"回放过程出错: {e}")
        finally:
            # 确保在UI线程中更新界面
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
        self.log_text.delete(1.0, tk.END)
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
            
            self.log_text.delete(1.0, tk.END)
            for action in self.actions:
                if action['type'] == 'move':
                    self.log_text.insert(tk.END, f"移动到: ({action['x']}, {action['y']})\n")
                elif action['type'] == 'click':
                    self.log_text.insert(tk.END, f"点击 {action['button']}: ({action['x']}, {action['y']})\n")
            
            self.status_var.set(f"已加载 {len(self.actions)} 个动作")
        except Exception as e:
            messagebox.showerror("错误", f"加载失败: {str(e)}")

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