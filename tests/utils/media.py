from pathlib import Path
from typing import Optional


def get_media_duration(file_path: Path) -> Optional[int]:
    """
    获取视频/音频文件的时长（毫秒）

    参数:
        file_path: 媒体文件路径

    返回:
        时长（毫秒），如果无法检测则返回None
    """
    try:
        # 使用ffmpeg-python库检测时长（需要先安装：pip install ffmpeg-python）
        import ffmpeg
        probe = ffmpeg.probe(str(file_path))
        duration = float(probe['format']['duration']) * 1000  # 秒转毫秒
        return int(duration)
    except ImportError:
        print("Warning: ffmpeg-python not installed, cannot auto-detect media duration")
        return None
    except Exception as e:
        print(f"Warning: Could not detect media duration: {e}")
        return None
