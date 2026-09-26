import cv2

DOCUMENT_IMAGE = "face_test/fictional_person_1.jpg"
SELFIE_IMAGE = "face_test/fictional_person_1_selfie.jpg"

DETECTOR_MODEL = "face_test/face_detection_yunet_2023mar.onnx"
RECOGNITION_MODEL = "face_test/face_recognition_sface_2021dec.onnx"


def detect_face(image, detector):
    detector.setInputSize((image.shape[1], image.shape[0]))
    _, faces = detector.detect(image)

    if faces is None:
        return None

    return faces[0]


document = cv2.imread(DOCUMENT_IMAGE)
selfie = cv2.imread(SELFIE_IMAGE)

if document is None:
    print("ERROR: Could not load document image.")
    exit()

if selfie is None:
    print("ERROR: Could not load selfie image.")
    exit()


detector = cv2.FaceDetectorYN.create(
    DETECTOR_MODEL,
    "",
    (document.shape[1], document.shape[0])
)

document_face = detect_face(document, detector)
selfie_face = detect_face(selfie, detector)

print("----- FACE SCREENING -----")

if document_face is None:
    print("Document face detected: NO")
    exit()

print("Document face detected: YES")

if selfie_face is None:
    print("Selfie face detected: NO")
    exit()

print("Selfie face detected: YES")


recognizer = cv2.FaceRecognizerSF.create(
    RECOGNITION_MODEL,
    ""
)

document_crop = recognizer.alignCrop(document, document_face)
selfie_crop = recognizer.alignCrop(selfie, selfie_face)

document_feature = recognizer.feature(document_crop)
selfie_feature = recognizer.feature(selfie_crop)

similarity = recognizer.match(
    document_feature,
    selfie_feature,
    cv2.FaceRecognizerSF_FR_COSINE
)

print("Cosine similarity:", similarity)
if similarity >= 0.6:
    print("Result: FACE MATCH")
else:
    print("Result: FACE MISMATCH")
print("-------------------------")