import tkinter as tk
import serial
import cv2
from PIL import Image, ImageTk
import time

SERIAL_BAUD = 115200
WINDOW_W, WINDOW_H = 600, 800
SMOOTHING = 0.2
SHOOT_MIN, SHOOT_MAX = 55, 166
SHOOT_HOLD_MS = 700
class SerialSender:
    def __init__(self, port, baud=115200):
        self.port = port
        self.baud = baud
        self.ser = None
        self.connect()

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
            time.sleep(1)
            print("Połączono z:", self.port)
        except Exception as e:
            print("Błąd połączenia:", e)
            self.ser = None

    def send(self, msg):
        if not self.ser:
            return
        if not msg.endswith("\n"):
            msg += "\n"
        try:
            self.ser.write(msg.encode('utf-8'))
        except Exception as e:
            print("Błąd wysyłania:", e)
            self.ser = None

    def close(self):
        if self.ser:
            try:
                self.ser.close()
            except:
                pass
            self.ser = None


class App:
    def __init__(self, master, sender, cam_index=2):
        self.master = master
        self.sender = sender
        master.title("Cursor → Servo Control + Camera (Rotated 90°)")
        master.geometry(f"{WINDOW_W}x{WINDOW_H}")

        self.cap = cv2.VideoCapture(cam_index)
        self.cam_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.cam_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.canvas = tk.Canvas(master, width=WINDOW_W, height=WINDOW_H)
        self.canvas.pack()

        self.target_pan = 90.0
        self.target_tilt = 90.0
        self.current_pan = 90.0
        self.current_tilt = 90.0

        self.cross = self.canvas.create_oval(0, 0, 10, 10, outline="red", width=2)
        self.txt = self.canvas.create_text(10, 10, anchor="nw", fill="white", text="")
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)

        self.shooting = False
        self.update_loop()

    def map_xy_to_angles(self, x, y):
        pan = (x / (WINDOW_W - 1)) * 180.0
        tilt = (1.0 - (y / (WINDOW_H - 1))) * 60.0 + 80.0
        return pan, tilt

    def on_mouse_move(self, event):
        x = max(0, min(WINDOW_W - 1, event.x))
        y = max(0, min(WINDOW_H - 1, event.y))
        self.target_pan, self.target_tilt = self.map_xy_to_angles(x, y)
        size = 6
        self.canvas.coords(self.cross, x - size, y - size, x + size, y + size)

    def on_mouse_down(self, event):
        if not self.shooting:
            self.shooting = True
            self.sender.send(f"S:{SHOOT_MIN}")
            self.master.after(SHOOT_HOLD_MS, self.reset_shoot)

    def reset_shoot(self):
        self.sender.send(f"S:{SHOOT_MAX}")
        self.shooting = False

    def update_loop(self):
        self.current_pan += (self.target_pan - self.current_pan) * SMOOTHING
        self.current_tilt += (self.target_tilt - self.current_tilt) * SMOOTHING

        pan_int = int(round(self.current_pan))
        tilt_int = int(round(self.current_tilt))

        if abs(pan_int - getattr(self, "_last_pan", -999)) >= 1:
            self.sender.send(f"P:{pan_int}")
            self._last_pan = pan_int
        if abs(tilt_int - getattr(self, "_last_tilt", -999)) >= 1:
            self.sender.send(f"T:{tilt_int}")
            self._last_tilt = tilt_int

        ret, frame = self.cap.read()
        if ret:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            frame = cv2.resize(frame, (WINDOW_W, WINDOW_H))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            self.photo = ImageTk.PhotoImage(image=img)
            self.canvas.create_image(0, 0, anchor="nw", image=self.photo)

        self.canvas.itemconfigure(
            self.txt,
            text=f"PAN: {pan_int}°  TILT: {tilt_int}°\nPort: {self.sender.port}"
        )

        self.master.after(20, self.update_loop)

    def __del__(self):
        if hasattr(self, "cap") and self.cap.isOpened():
            self.cap.release()


def main():
    port = "COM3"
    sender = SerialSender(port=port, baud=SERIAL_BAUD)
    root = tk.Tk()
    app = App(root, sender)
    try:
        root.mainloop()
    finally:
        sender.close()


if __name__ == "__main__":
    main()
