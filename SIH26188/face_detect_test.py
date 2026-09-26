import cv2

image = cv2.imread("face_test/lena.jpg")

height, width = image.shape[:2]

detector = cv2.FaceDetectorYN.create(
    "face_test/face_detection_yunet_2023mar.onnx",
    "",
    (width, height)
)

_, faces = detector.detect(image)

if faces is None:
    print("Faces detected: 0")
else:
    print("Faces detected:", len(faces))
    print(faces)