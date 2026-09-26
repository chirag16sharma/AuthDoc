\# SIH26188 — Document \& Face Screening Module



This folder contains the independent development and testing work for the \*\*SIH26188 AI-Based Fake Identity \& Document Screening System\*\*.



The current implementation focuses on two core capabilities:



\- \*\*OCR-based document text extraction\*\*

\- \*\*Face detection and face-to-selfie comparison\*\*



The implementation is currently a \*\*proof-of-concept/demo\*\*, using fictional or synthetic test data.



\## Features Implemented



\### 1. OCR



Uses \*\*Tesseract OCR\*\* with Python and Pillow to extract text from an identity-document image.



The current test document contains fictional information such as:



\- Name

\- Date of birth

\- Document number

\- Valid-until date



The extracted text can then be used by later validation and screening components.



\### 2. Face Detection



Uses \*\*OpenCV YuNet\*\* to detect faces in document and selfie images.



The detector is tested on sample images and is used as the first stage of the face-screening process.



\### 3. Face Comparison



Uses \*\*OpenCV SFace\*\* to generate face features and calculate cosine similarity between:



\- The face detected in the document

\- The face detected in the selfie



The current proof of concept can demonstrate both:



\- \*\*FACE MATCH\*\*

\- \*\*FACE MISMATCH\*\*



The similarity threshold used in the current demo is a prototype threshold and should not be treated as a universal biometric verification standard.



\## Project Structure



```text

SIH26188/

├── README.md

├── .gitignore

├── create\_test\_image.py

├── ocr\_test.py

├── face\_detect\_test.py

├── face\_compare.py

├── test\_images/

│   └── fictional\_id.png

└── face\_test/

&#x20;   ├── face\_detection\_yunet\_2023mar.onnx

&#x20;   └── face\_recognition\_sface\_2021dec.onnx

```



\## Technologies



\- Python

\- Tesseract OCR

\- Pytesseract

\- Pillow

\- OpenCV

\- YuNet

\- SFace



\## Testing



The current module has been tested with:



\- A fictional identity document

\- Face detection

\- Same-person face comparison

\- Different-person face comparison



The test data is intended for development and demonstration only.



\## Current Limitations



This module is currently a proof of concept.



It does \*\*not\*\*:



\- Verify an identity against a government database

\- Prove that a document is genuine or forged

\- Perform production-grade biometric authentication

\- Establish real-world fraud-detection accuracy



Further integration with document validation, tampering analysis, risk scoring, and the team's main application is required for a complete screening system.



\## Purpose



The goal of this module is to provide \*\*evidence and screening signals\*\* that can assist a reviewer, rather than treating an automated result as definitive proof of identity or fraud.

