import argparse
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from mss import mss


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Windows masaüstünde ekran kaydı almak için basit bir araç."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"),
        help="Çıktı dosyası yolu (varsayılan: recording_YYYYMMDD_HHMMSS.mp4)",
    )
    parser.add_argument("--fps", type=int, default=30, help="Kayıt FPS değeri")
    parser.add_argument(
        "--monitor",
        type=int,
        default=1,
        help="Kaydedilecek monitör numarası (mss monitor index'i)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0,
        help="Saniye cinsinden kayıt süresi. 0 ise Ctrl+C ile durdurulur.",
    )
    return parser.parse_args()


def create_writer(output: Path, fps: int, width: int, height: int) -> cv2.VideoWriter:
    output.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output), fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError("VideoWriter başlatılamadı. Codec veya yol kontrolü yapın.")
    return writer


def record_screen(output: Path, fps: int, monitor_index: int, duration: float) -> None:
    with mss() as sct:
        monitors = sct.monitors
        if monitor_index < 1 or monitor_index >= len(monitors):
            raise ValueError(
                f"Geçersiz monitor index: {monitor_index}. Kullanılabilir aralık: 1-{len(monitors) - 1}"
            )

        monitor = monitors[monitor_index]
        width = monitor["width"]
        height = monitor["height"]

        writer = create_writer(output, fps, width, height)
        frame_interval = 1.0 / fps
        start_time = time.time()
        frame_count = 0

        print(f"Kayıt başladı: {output}")
        print("Durdurmak için Ctrl+C kullanın.")

        try:
            while True:
                loop_start = time.time()
                screenshot = sct.grab(monitor)
                frame = np.array(screenshot)
                bgr_frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                writer.write(bgr_frame)
                frame_count += 1

                if duration > 0 and (time.time() - start_time) >= duration:
                    break

                elapsed = time.time() - loop_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
        except KeyboardInterrupt:
            print("Kayıt kullanıcı tarafından durduruldu.")
        finally:
            writer.release()

        total_time = max(time.time() - start_time, 0.001)
        avg_fps = frame_count / total_time
        print(f"Kayıt tamamlandı. Toplam kare: {frame_count}, Ortalama FPS: {avg_fps:.2f}")


def main() -> None:
    args = parse_args()
    record_screen(args.output, args.fps, args.monitor, args.duration)


if __name__ == "__main__":
    main()