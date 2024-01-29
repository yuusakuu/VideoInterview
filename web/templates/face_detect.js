import DeviceDetector from "https://cdn.skypack.dev/device-detector-js@2.2.10";
testSupport([
    { client: 'Chrome' },
]);
// 현재 브라우저 확인
function testSupport(supportedDevices) {
    const deviceDetector = new DeviceDetector();
    const detectedDevice = deviceDetector.parse(navigator.userAgent);
    let isSupported = false;
    for (const device of supportedDevices) {
        if (device.client !== undefined) {
            const re = new RegExp(`^${device.client}$`);
            if (!re.test(detectedDevice.client.name)) {
                continue;
            }
        }
        if (device.os !== undefined) {
            const re = new RegExp(`^${device.os}$`);
            if (!re.test(detectedDevice.os.name)) {
                continue;
            }
        }
        isSupported = true;
        break;
    }
    // 지원하지 않는 브라우저
    if (!isSupported) {
        alert(`This demo, running on ${detectedDevice.client.name}/${detectedDevice.os.name}, ` +
            `is not well supported at this time, continue at your own risk.`);
    }
}
const controls = window;
const drawingUtils = window;
const mpFaceDetection = window;
// 입력
const videoElement = document.getElementsByClassName('input_video')[0]; // 영상 
const canvasElement = document.getElementsByClassName('output_canvas')[0]; // 캔버스 
const controlsElement = document.getElementsByClassName('control-panel')[0]; // control pannel 
const canvasCtx = canvasElement.getContext('2d');// 캔버스 다를 때 기본 세팅  

// mediapipe 실행
const faceDetection = new mpFaceDetection.FaceDetection({ locateFile: (file) => {
    return `https://cdn.jsdelivr.net/npm/@mediapipe/face_detection@0.4/${file}`;
} });
faceDetection.onResults(onResults);

// tick() 실행을 위해 추가. 아래 control-pannel에 추가 예정
const fpsControl = new controls.FPS();
// mediapipe 실행 결과
function onResults(results) {
    // 로딩완료
    document.body.classList.add('loaded');
    // fps 업데이트
    fpsControl.tick();
    // 영상위에 결과 출력
    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
    canvasCtx.drawImage(results.image, 0, 0, canvasElement.width, canvasElement.height);
    if (results.detections.length > 0) {
        drawingUtils.drawRectangle(canvasCtx, results.detections[0].boundingBox, { color: 'blue', lineWidth: 4, fillColor: '#00000000' });
        drawingUtils.drawLandmarks(canvasCtx, results.detections[0].landmarks, {
            color: 'red',
            radius: 5,
        });
    }
    canvasCtx.restore();
}

// control pannel
new controls
    // 초기값 설정
    .ControlPanel(controlsElement, {
    selfieMode: true, // 좌우반전 설정
    model: 'short', // 얼굴 거리설정
    minDetectionConfidence: 0.5,
})
    // 패널 내용 추가
    .add([
    new controls.StaticText({ title: 'MediaPipe Face Detection' }), //제목
    fpsControl, // fps
    new controls.Toggle({ title: 'Selfie Mode', field: 'selfieMode' }), // 좌우반전 설정
    new controls.SourcePicker({ // 소스 설정 (영상/사진)
        onSourceChanged: () => { // 소스 바뀌면 리셋 
            faceDetection.reset();
        },
        onFrame: async (input, size) => {
            const aspect = size.height / size.width;
            let width, height;
            if (window.innerWidth > window.innerHeight) {
                height = window.innerHeight;
                width = height / aspect;
            }
            else {
                width = window.innerWidth;
                height = width * aspect;
            }
            canvasElement.width = width;
            canvasElement.height = height;
            await faceDetection.send({ image: input });
        },
        examples: {
            images: [],
            videos: [],
        },
    }),
    new controls.Slider({ // short:2m이내에 얼굴이 있을떄 full:5m이내에 얼굴이 있을때
        title: 'Model Selection',
        field: 'model',
        discrete: { 'short': 'Short-Range', 'full': 'Full-Range' },
    }),
    new controls.Slider({ // 모델의 최소 신뢰값
        title: 'Min Detection Confidence',
        field: 'minDetectionConfidence',
        range: [0, 1],
        step: 0.01
    }),
])
    .on(x => {
    const options = x;
    videoElement.classList.toggle('selfie', options.selfieMode);
    faceDetection.setOptions(options);
});