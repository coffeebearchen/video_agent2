import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, scrolledtext

# =========================================================
# scene_editor.py
# 最小对齐 Schema V1 的本地编辑器
# 目标：
# 1. 兼容旧 scene_plan.json
# 2. 保存时统一输出 Schema V1
# 3. 保持“生成语音 / 生成视频”按钮可用
# 4. 不改主链其他模块
# =========================================================

# ---------- 基础路径 ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCENE_PATH_CANDIDATES = [
    os.path.join(BASE_DIR, "data", "current", "scene_plan.json"),
    os.path.join(BASE_DIR, "scene_plan.json"),
]

DEFAULT_SAVE_PATH = os.path.join(BASE_DIR, "data", "current", "scene_plan.json")

SCHEMA_VERSION = "1.0"
DEFAULT_SOURCE_TYPE = "mixed"
DEFAULT_SCENE_COUNT = 5
DEFAULT_DURATION = 4


class SceneEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Scene Editor - Schema V1")
        self.root.geometry("1050x860")

        # 当前加载的文件路径
        self.current_scene_path = self.find_existing_scene_file()

        # 当前内存中的标准化数据
        self.scene_data = self.build_empty_scene_data()

        # UI 引用
        self.title_var = tk.StringVar()
        self.info_var = tk.StringVar()
        self.scene_text_widgets = []
        self.scene_duration_vars = []

        self.build_ui()
        self.load_scene_on_startup()

    # =====================================================
    # 数据层：构造 / 标准化 / 兼容
    # =====================================================

    def find_existing_scene_file(self):
        for path in SCENE_PATH_CANDIDATES:
            if os.path.exists(path):
                return path
        return DEFAULT_SAVE_PATH

    def build_empty_scene_data(self):
        return {
            "schema_version": SCHEMA_VERSION,
            "title": "",
            "source_type": DEFAULT_SOURCE_TYPE,
            "total_scenes": DEFAULT_SCENE_COUNT,
            "scenes": [
                {
                    "scene_id": i + 1,
                    "text": "",
                    "duration": DEFAULT_DURATION
                }
                for i in range(DEFAULT_SCENE_COUNT)
            ]
        }

    def normalize_scene_data(self, raw_data):
        """
        把旧格式 / 不完整格式，统一转成内部标准结构
        """
        if not isinstance(raw_data, dict):
            raw_data = {}

        title = raw_data.get("title", "")
        schema_version = raw_data.get("schema_version", SCHEMA_VERSION)
        source_type = raw_data.get("source_type", DEFAULT_SOURCE_TYPE)

        raw_scenes = raw_data.get("scenes", [])
        if not isinstance(raw_scenes, list):
            raw_scenes = []

        normalized_scenes = []

        # 当前阶段仍默认固定 5 段
        target_count = DEFAULT_SCENE_COUNT

        for i in range(target_count):
            if i < len(raw_scenes) and isinstance(raw_scenes[i], dict):
                raw_scene = raw_scenes[i]
            else:
                raw_scene = {}

            scene_id = raw_scene.get("scene_id", i + 1)
            text = raw_scene.get("text", "")
            duration = raw_scene.get("duration", DEFAULT_DURATION)

            # scene_id 保护
            if not isinstance(scene_id, int) or scene_id <= 0:
                scene_id = i + 1

            # text 保护
            if text is None:
                text = ""
            text = str(text)

            # duration 保护
            if isinstance(duration, bool):
                duration = DEFAULT_DURATION
            if not isinstance(duration, (int, float)):
                duration = DEFAULT_DURATION
            if duration <= 0:
                duration = DEFAULT_DURATION

            # 当前保存时统一用 int
            duration = int(round(duration))

            normalized_scenes.append({
                "scene_id": i + 1,   # 保存时统一重排，避免乱序
                "text": text,
                "duration": duration
            })

        normalized = {
            "schema_version": schema_version if schema_version else SCHEMA_VERSION,
            "title": str(title) if title is not None else "",
            "source_type": str(source_type) if source_type else DEFAULT_SOURCE_TYPE,
            "total_scenes": target_count,
            "scenes": normalized_scenes
        }

        return normalized

    def collect_ui_to_scene_data(self):
        """
        从界面取值，重新组装成 Schema V1 标准格式
        """
        title = self.title_var.get().strip()

        scenes = []
        for i in range(DEFAULT_SCENE_COUNT):
            text_widget = self.scene_text_widgets[i]
            duration_var = self.scene_duration_vars[i]

            text = text_widget.get("1.0", tk.END).strip()

            # duration 安全处理
            raw_duration = duration_var.get().strip()
            try:
                duration = int(float(raw_duration))
            except Exception:
                duration = DEFAULT_DURATION

            if duration <= 0:
                duration = DEFAULT_DURATION

            scenes.append({
                "scene_id": i + 1,
                "text": text,
                "duration": duration
            })

        return {
            "schema_version": SCHEMA_VERSION,
            "title": title,
            "source_type": DEFAULT_SOURCE_TYPE,
            "total_scenes": DEFAULT_SCENE_COUNT,
            "scenes": scenes
        }

    # =====================================================
    # UI 构建
    # =====================================================

    def build_ui(self):
        # 顶部操作区
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=10)

        tk.Button(top_frame, text="加载 Scene", width=14, command=self.load_scene).pack(side="left", padx=5)
        tk.Button(top_frame, text="保存 Scene", width=14, command=self.save_scene).pack(side="left", padx=5)
        tk.Button(top_frame, text="生成语音", width=14, command=self.generate_audio).pack(side="left", padx=5)
        tk.Button(top_frame, text="生成视频", width=14, command=self.generate_video).pack(side="left", padx=5)

        # 文件信息区
        info_frame = tk.Frame(self.root)
        info_frame.pack(fill="x", padx=10, pady=(0, 10))

        tk.Label(info_frame, text="当前文件：", anchor="w").pack(side="left")
        tk.Label(info_frame, textvariable=self.info_var, fg="blue", anchor="w").pack(side="left", padx=6)

        # 标题区
        title_frame = tk.Frame(self.root)
        title_frame.pack(fill="x", padx=10, pady=(0, 10))

        tk.Label(title_frame, text="标题：", width=8, anchor="w").pack(side="left")
        tk.Entry(title_frame, textvariable=self.title_var, font=("Arial", 12)).pack(fill="x", expand=True, side="left")

        # 说明区
        hint_frame = tk.Frame(self.root)
        hint_frame.pack(fill="x", padx=10, pady=(0, 10))

        hint_text = (
            "说明：当前编辑器已最小对齐 Schema V1。\n"
            "重点编辑 text；duration 可改，但当前不要发散做复杂控制。"
        )
        tk.Label(hint_frame, text=hint_text, justify="left", fg="#444").pack(anchor="w")

        # scenes 编辑区
        scenes_container = tk.Frame(self.root)
        scenes_container.pack(fill="both", expand=True, padx=10, pady=10)

        for i in range(DEFAULT_SCENE_COUNT):
            block = tk.LabelFrame(scenes_container, text=f"Scene {i + 1}", padx=8, pady=8)
            block.pack(fill="x", expand=False, pady=6)

            # duration 行
            duration_row = tk.Frame(block)
            duration_row.pack(fill="x", pady=(0, 6))

            tk.Label(duration_row, text="Duration (秒)：", width=14, anchor="w").pack(side="left")
            duration_var = tk.StringVar(value=str(DEFAULT_DURATION))
            duration_entry = tk.Entry(duration_row, textvariable=duration_var, width=8)
            duration_entry.pack(side="left")

            self.scene_duration_vars.append(duration_var)

            # text 行
            text_widget = scrolledtext.ScrolledText(block, height=5, wrap=tk.WORD, font=("Arial", 11))
            text_widget.pack(fill="x", expand=True)

            self.scene_text_widgets.append(text_widget)

    # =====================================================
    # 加载 / 保存
    # =====================================================

    def load_scene_on_startup(self):
        if os.path.exists(self.current_scene_path):
            self.load_scene()
        else:
            self.scene_data = self.build_empty_scene_data()
            self.fill_ui_from_scene_data()
            self.update_info_label("未找到现有 scene_plan.json，已加载空白模板")

    def load_scene(self):
        try:
            path = self.find_existing_scene_file()
            self.current_scene_path = path

            if not os.path.exists(path):
                self.scene_data = self.build_empty_scene_data()
                self.fill_ui_from_scene_data()
                self.update_info_label("未找到 scene_plan.json，已加载空白模板")
                return

            with open(path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            self.scene_data = self.normalize_scene_data(raw_data)
            self.fill_ui_from_scene_data()
            self.update_info_label(f"已加载：{path}")

        except Exception as e:
            messagebox.showerror("加载失败", f"加载 scene 失败：\n{e}")

    def fill_ui_from_scene_data(self):
        self.title_var.set(self.scene_data.get("title", ""))

        scenes = self.scene_data.get("scenes", [])
        for i in range(DEFAULT_SCENE_COUNT):
            scene = scenes[i] if i < len(scenes) else {
                "scene_id": i + 1,
                "text": "",
                "duration": DEFAULT_DURATION
            }

            text = scene.get("text", "")
            duration = scene.get("duration", DEFAULT_DURATION)

            self.scene_text_widgets[i].delete("1.0", tk.END)
            self.scene_text_widgets[i].insert(tk.END, text)

            self.scene_duration_vars[i].set(str(duration))

    def save_scene(self):
        try:
            data = self.collect_ui_to_scene_data()

            save_path = DEFAULT_SAVE_PATH
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.scene_data = data
            self.current_scene_path = save_path
            self.update_info_label(f"已保存：{save_path}")
            messagebox.showinfo("保存成功", "Scene 已按 Schema V1 保存成功。")

        except Exception as e:
            messagebox.showerror("保存失败", f"保存 scene 失败：\n{e}")

    def update_info_label(self, text):
        self.info_var.set(text)

    # =====================================================
    # 调用外部脚本
    # =====================================================

    def run_python_script(self, script_name):
        script_path = os.path.join(BASE_DIR, script_name)

        if not os.path.exists(script_path):
            messagebox.showerror("文件不存在", f"未找到脚本：\n{script_path}")
            return False

        try:
            result = subprocess.run(
                [sys.executable, script_path],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            if result.returncode != 0:
                error_text = (
                    f"脚本执行失败：{script_name}\n\n"
                    f"返回码：{result.returncode}\n\n"
                    f"STDOUT:\n{result.stdout}\n\n"
                    f"STDERR:\n{result.stderr}"
                )
                messagebox.showerror("执行失败", error_text)
                return False

            return True

        except Exception as e:
            messagebox.showerror("执行异常", f"执行 {script_name} 时出错：\n{e}")
            return False

    def generate_audio(self):
        # 先保存，再生成语音
        try:
            self.save_scene()
        except Exception:
            return

        ok = self.run_python_script("tts_engine_main.py")
        if ok:
            messagebox.showinfo("完成", "语音生成完成。")

    def generate_video(self):
        # 先保存，再生成视频
        try:
            self.save_scene()
        except Exception:
            return

        ok = self.run_python_script("video_engine.py")
        if ok:
            messagebox.showinfo("完成", "视频生成完成。")


def main():
    root = tk.Tk()
    app = SceneEditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()