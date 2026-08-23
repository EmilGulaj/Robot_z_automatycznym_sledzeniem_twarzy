import cv2
import mediapipe as mp
import serial
import time

# Dodać lekki cooldown jak zobaczy środkowy palec, żeby nie strzelał od razu gdy tylko zniknie, tylko jakoś po sekundzie/dwóch

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

SERIAL_PORT = "COM3"
BAUD_RATE = 115200

FRAME_WIDTH = 640
FRAME_HEIGHT = 480

PAN_MIN = 0
PAN_MAX = 180

TILT_MIN = 60
TILT_MAX = 140

SHOOT_MIN = 55
SHOOT_MAX = 166
SHOOT_HOLD = 0.7

AUTO_SHOOT_COOLDOWN = 1.2
fire_zone = 15

K_pan = 0.028
K_tilt = 0.028

deadzone = 12
max_step = 3.5

lost_threshold = 0.6

current_pan = 90
current_tilt = 110

shooting = False
shoot_time = 0

last_auto_shot = 0

last_seen = time.time()

search_direction = 1

current_led = -1

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)

time.sleep(1)

def set_led(mode):

    global current_led

    if current_led != mode:

        ser.write(f"L:{mode}\n".encode())

        current_led = mode

def send_pan(val):

    global current_pan

    val = int(max(PAN_MIN, min(PAN_MAX, val)))

    if val != current_pan:

        ser.write(f"P:{val}\n".encode())

        current_pan = val

def send_tilt(val):

    global current_tilt

    val = int(max(TILT_MIN, min(TILT_MAX, val)))

    if val != current_tilt:

        ser.write(f"T:{val}\n".encode())

        current_tilt = val

def shoot():

    global shooting
    global shoot_time

    if not shooting:

        shooting = True

        shoot_time = time.time()

        set_led(2)

        ser.write(f"S:{SHOOT_MIN}\n".encode())

base_options = python.BaseOptions(
    model_asset_path="face_detector.tflite"
)

options = vision.FaceDetectorOptions(
    base_options=base_options,
    min_detection_confidence=0.65
)

detector = vision.FaceDetector.create_from_options(options)

mp_hands = mp.solutions.hands

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.55,
    min_tracking_confidence=0.55
)

def middle_finger_detected(hand_landmarks):

    tips = {
        "thumb": 4,
        "index": 8,
        "middle": 12,
        "ring": 16,
        "pinky": 20
    }

    pips = {
        "index": 6,
        "middle": 10,
        "ring": 14,
        "pinky": 18
    }

    middle_up = (
        hand_landmarks.landmark[tips["middle"]].y <
        hand_landmarks.landmark[pips["middle"]].y
    )

    index_down = (
        hand_landmarks.landmark[tips["index"]].y >
        hand_landmarks.landmark[pips["index"]].y
    )

    ring_down = (
        hand_landmarks.landmark[tips["ring"]].y >
        hand_landmarks.landmark[pips["ring"]].y
    )

    pinky_down = (
        hand_landmarks.landmark[tips["pinky"]].y >
        hand_landmarks.landmark[pips["pinky"]].y
    )

    return (
        middle_up
        and index_down
        and ring_down
        and pinky_down
    )

cap = cv2.VideoCapture(2)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

set_led(0)

while True:

    ret, frame = cap.read()

    if not ret:
        break

    frame = cv2.rotate(
        frame,
        cv2.ROTATE_90_CLOCKWISE
    )

    rot_w = FRAME_HEIGHT
    rot_h = FRAME_WIDTH

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    hand_results = hands.process(rgb)

    disable_shooting = False

    if hand_results.multi_hand_landmarks:

        for hand_landmarks in hand_results.multi_hand_landmarks:

            if middle_finger_detected(hand_landmarks):

                disable_shooting = True

                set_led(3)

                cv2.putText(
                    frame,
                    "FIRE DISABLED",
                    (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    3
                )

                time.sleep(1)

                break

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb
    )

    detection_result = detector.detect(mp_image)

    now = time.time()

    if shooting and now - shoot_time >= SHOOT_HOLD:

        ser.write(f"S:{SHOOT_MAX}\n".encode())

        shooting = False

        set_led(1)

    if detection_result.detections:

        if not disable_shooting and not shooting:
            set_led(1)

        last_seen = now

        detection = detection_result.detections[0]

        bbox = detection.bounding_box

        x = bbox.origin_x
        y = bbox.origin_y
        w = bbox.width
        h = bbox.height

        cx = int(x + w / 2)
        cy = int(y + h / 2)

        center_x = rot_w // 2
        center_y = rot_h // 2

        error_pan = center_x - cx
        error_tilt = center_y - cy

        if abs(error_pan) < deadzone:
            error_pan = 0

        if abs(error_tilt) < deadzone:
            error_tilt = 0

        pan_change = max(
            -max_step,
            min(max_step, error_pan * K_pan)
        )

        tilt_change = max(
            -max_step,
            min(max_step, error_tilt * K_tilt)
        )

        new_pan = current_pan + pan_change
        new_tilt = current_tilt + tilt_change

        send_pan(int(new_pan))
        send_tilt(int(new_tilt))

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )

        cv2.circle(
            frame,
            (cx, cy),
            8,
            (0, 255, 0),
            -1
        )

        if (
            max(abs(error_pan), abs(error_tilt)) < fire_zone
            and not disable_shooting
        ):

            if now - last_auto_shot > AUTO_SHOOT_COOLDOWN:

                shoot()

                last_auto_shot = now

    else:

        if not disable_shooting:
            set_led(0)

        if now - last_seen > lost_threshold:

            current_pan += search_direction * 1.4

            if current_pan >= PAN_MAX:

                current_pan = PAN_MAX
                search_direction = -1

            if current_pan <= PAN_MIN:

                current_pan = PAN_MIN
                search_direction = 1

            send_pan(int(current_pan))

    cv2.circle(
        frame,
        (rot_w // 2, rot_h // 2),
        6,
        (255, 0, 0),
        -1
    )

    cv2.imshow(
        "Tracking + Auto Shoot + Middle Finger Disable",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()

ser.close()

cv2.destroyAllWindows()