try:
    from PIL import Image, ImageDraw
    import os
    import sys
    
    def create_mouse_icon(output_file="mouse_icon.ico", size=128):
        try:
            print(f"创建鼠标图标: {output_file}")
            
            # 创建一个透明的图像
            img = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # 设置颜色
            pointer_color = (30, 144, 255)  # 蓝色鼠标指针
            outline_color = (255, 255, 255)  # 白色边框
            
            # 计算尺寸
            margin = size // 8
            width = size - 2 * margin
            height = width
            
            # 绘制鼠标形状 (更像鼠标)
            body_points = [
                (margin, margin),                      # 左上角
                (margin, margin + height * 2 // 3),    # 左中
                (margin + width // 3, margin + height),  # 底部
                (margin + width // 2, margin + height * 3 // 4),  # 右下凹口
                (margin + width, margin + height // 3),  # 右侧点
                (margin + width * 2 // 3, margin),      # 右上凹口
            ]
            
            # 绘制阴影效果
            shadow_offset = size // 50
            shadow_points = [(x + shadow_offset, y + shadow_offset) for x, y in body_points]
            draw.polygon(shadow_points, fill=(0, 0, 0, 100))
            
            # 绘制主体
            draw.polygon(body_points, fill=pointer_color, outline=outline_color)
            
            # 绘制按钮
            button_y = margin + height // 4
            button_width = width // 3
            draw.line([(margin + width // 3, button_y), 
                      (margin + width * 2 // 3, button_y)], 
                      fill=outline_color, width=2)
            
            # 保存为多种尺寸的ICO文件
            sizes = [16, 32, 48, 64, 128]
            resized_images = []
            
            for s in sizes:
                resized = img.resize((s, s), Image.LANCZOS)
                resized_images.append(resized)
            
            if os.path.exists(output_file):
                os.remove(output_file)
                
            img.save(output_file, format='ICO', sizes=[(s, s) for s in sizes])
            print(f"图标已创建: {output_file}")
            return True
        except Exception as e:
            print(f"创建图标时出错: {str(e)}")
            # 创建一个简单的替代图标
            try:
                simple_img = Image.new('RGB', (64, 64), color=(30, 144, 255))
                simple_img.save(output_file, format='ICO')
                print(f"已创建简单替代图标: {output_file}")
                return True
            except:
                print("无法创建任何图标")
                return False
    
    if __name__ == "__main__":
        create_mouse_icon()

except ImportError:
    print("警告: 无法导入PIL库，将无法创建图标")
    # 创建一个空文件作为占位符
    try:
        with open("mouse_icon.ico", "wb") as f:
            f.write(b"")
        print("已创建空图标文件")
    except:
        print("无法创建图标文件") 