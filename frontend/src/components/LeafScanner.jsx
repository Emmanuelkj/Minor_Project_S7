import React, { useState, useRef, useEffect, useCallback } from 'react';
import { 
  Camera,
  UploadCloud, 
  ScanLine, 
  CheckCircle, 
  AlertTriangle, 
  ShieldAlert, 
  Sparkles, 
  FileCheck,
  RefreshCw,
  FlaskConical,
  Sprout,
  VideoOff
} from 'lucide-react';

export default function LeafScanner({ onAnalyzeCompleted }) {
  // Input mode: 'camera' (default primary) or 'upload'
  const [inputMode, setInputMode] = useState('camera');
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [diagnosisResult, setDiagnosisResult] = useState(null);
  const [selectedCrop, setSelectedCrop] = useState('');
  const [errorMsg, setErrorMsg] = useState(null);
  const [cameraLoading, setCameraLoading] = useState(false);

  // References for live video stream and capture canvas
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  // Request ID ref guards against slow getUserMedia resolving after stop/unmount
  const requestIdRef = useRef(0);

  // Helper to stop all active camera tracks so webcam hardware light turns off
  const stopCameraStream = useCallback(() => {
    // Invalidate any in-flight camera request
    requestIdRef.current += 1;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraLoading(false);
  }, []);

  // Helper to start camera stream with proper permission and device handling
  const startCameraStream = useCallback(async () => {
    // Stop any existing stream first
    stopCameraStream();

    // Check if mediaDevices API is supported (requires HTTPS or localhost)
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setErrorMsg('Camera access is not supported by your browser or requires a secure context (HTTPS or localhost).');
      return;
    }

    const currentReqId = ++requestIdRef.current;
    setCameraLoading(true);
    setErrorMsg(null);

    const constraints = {
      audio: false,
      video: {
        facingMode: 'environment',
        width: { ideal: 1280 },
        height: { ideal: 720 }
      }
    };

    try {
      const stream = await navigator.mediaDevices.getUserMedia(constraints);

      // If another request was started or component unmounted while waiting for user permission
      if (currentReqId !== requestIdRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setCameraLoading(false);
    } catch (err) {
      if (currentReqId !== requestIdRef.current) return;
      setCameraLoading(false);

      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setErrorMsg('Camera permission blocked. Please allow camera access in your browser settings.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setErrorMsg('No camera hardware found on this device.');
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        setErrorMsg('Camera is currently in use by another application or tab.');
      } else if (err.name === 'OverconstrainedError') {
        setErrorMsg('Requested camera resolution or constraints are not supported by your device.');
      } else {
        setErrorMsg(`Camera error: ${err.message || 'Unable to access camera.'}`);
      }
    }
  }, [stopCameraStream]);

  // Manage camera lifecycle based on mode and captured preview
  useEffect(() => {
    if (inputMode === 'camera' && !previewUrl) {
      startCameraStream();
    } else {
      stopCameraStream();
    }

    // Cleanup tracks on unmount
    return () => {
      stopCameraStream();
    };
  }, [inputMode, previewUrl, startCameraStream, stopCameraStream]);

  // Capture leaf frame from live video
  const handleCaptureLeaf = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth || !video.videoHeight) {
      setErrorMsg('Camera feed not ready yet. Please wait a moment and try again.');
      return;
    }

    const canvas = canvasRef.current || document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setErrorMsg('Failed to capture frame from camera.');
          return;
        }

        const file = new File([blob], `leaf_capture_${Date.now()}.jpg`, { type: 'image/jpeg' });
        const localUrl = URL.createObjectURL(blob);

        setSelectedFile(file);
        setPreviewUrl(localUrl);
        setDiagnosisResult(null);
        setErrorMsg(null);

        // Turn off camera stream once captured
        stopCameraStream();
      },
      'image/jpeg',
      0.92
    );
  };

  // Retake photo: clear captured frame and restart camera
  const handleRetakePhoto = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setDiagnosisResult(null);
    setErrorMsg(null);
    if (inputMode === 'camera') {
      startCameraStream();
    }
  };

  // Switch input modes safely
  const handleModeChange = (mode) => {
    if (mode === inputMode) return;
    stopCameraStream();
    setInputMode(mode);
    setSelectedFile(null);
    setPreviewUrl(null);
    setDiagnosisResult(null);
    setErrorMsg(null);
  };

  // Pre-loaded sample leaf image assets for instant quick demo testing
  const sampleLeafOptions = [
    {
      name: 'Early Blight (Tomato)',
      crop: 'Tomato',
      url: 'https://images.unsplash.com/photo-1592924357228-91a4daadcfea?auto=format&fit=crop&w=600&q=80',
      mockResult: {
        crop: 'Tomato',
        disease: 'Early Blight',
        scientific_name: 'Alternaria solani',
        status: 'Diseased',
        severity: 'Moderate',
        confidence: 96.4,
        symptoms: [
          'Concentric ring spots (bullseye pattern) on lower foliage',
          'Yellow chlorotic halos surrounding brown leaf lesions',
          'Defoliation starting from lower stem base'
        ],
        causes: 'High humidity (>80%) combined with leaf wetness and warm temps (24-29°C).',
        organic_remedies: [
          'Apply copper octanoate or bio-fungicide containing Bacillus subtilis.',
          'Prune lower infected foliage to enhance airflow.',
          'Mulch heavily around stem to reduce soil splash.'
        ],
        chemical_remedies: [
          'Apply Chlorothalonil or Mancozeb fungicide every 7-10 days.',
          'Spray Azoxystrobin upon early spot emergence.'
        ],
        preventive_measures: [
          'Practice 3-year crop rotation with non-solanaceous crops.',
          'Use drip irrigation instead of overhead sprayers.'
        ],
        recommendation: '[Diseased] Apply copper octanoate or bio-fungicide and prune lower leaves immediately.'
      }
    },
    {
      name: 'Late Blight (Potato)',
      crop: 'Potato',
      url: 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=600&q=80',
      mockResult: {
        crop: 'Potato',
        disease: 'Late Blight',
        scientific_name: 'Phytophthora infestans',
        status: 'Diseased',
        severity: 'Critical',
        confidence: 94.8,
        symptoms: [
          'Large purplish-black water-soaked leaf spots',
          'Velvety white fungal mold underneath leaves during wet weather',
          'Rapid brown foliage destruction'
        ],
        causes: 'Cool, wet, rainy weather with high humidity.',
        organic_remedies: [
          'Destroy infected vines before harvest.',
          'Apply fixed copper fungicides before rainy periods.'
        ],
        chemical_remedies: [
          'Apply systemic Mefenoxam or Metalaxyl mixed with Mancozeb.'
        ],
        preventive_measures: [
          'Plant certified pathogen-free seed tubers.',
          'Maintain high soil hilling around potato rows.'
        ],
        recommendation: '[Critical] Apply systemic Mefenoxam/Mancozeb immediately and hill soil up.'
      }
    },
    {
      name: 'Healthy Foliage (Tomato)',
      crop: 'Tomato',
      url: 'https://images.unsplash.com/photo-1530836369250-ef72a3f5cda8?auto=format&fit=crop&w=600&q=80',
      mockResult: {
        crop: 'Tomato',
        disease: 'Healthy Foliage',
        scientific_name: 'Solanum lycopersicum',
        status: 'Healthy',
        severity: 'None',
        confidence: 98.2,
        symptoms: ['Uniform green leaf coloration', 'Zero fungal lesions or pest spots'],
        causes: 'Optimal soil moisture and high solar radiation.',
        organic_remedies: ['Continue balanced compost feeding.'],
        chemical_remedies: ['No chemical treatment required.'],
        preventive_measures: ['Maintain regular leaf inspection and steady watering.'],
        recommendation: '[Healthy] Foliage is vibrant and healthy. Maintain current irrigation.'
      }
    }
  ];

  const handleFileChange = (e) => {
    stopCameraStream();
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setDiagnosisResult(null);
      setErrorMsg(null);
    }
  };

  const handleSelectSample = (sample) => {
    stopCameraStream();
    setPreviewUrl(sample.url);
    setSelectedFile(null);
    setDiagnosisResult(null);
    setErrorMsg(null);
    setSelectedCrop(sample.crop);

    // Simulate quick scan for preloaded samples or send request
    runSampleAnalysis(sample.mockResult);
  };

  const runSampleAnalysis = (mockRes) => {
    setIsScanning(true);
    setTimeout(() => {
      setIsScanning(false);
      setDiagnosisResult(mockRes);
      if (onAnalyzeCompleted) onAnalyzeCompleted(mockRes);
    }, 1800);
  };

  const handleUploadAndAnalyze = async () => {
    if (!selectedFile && !previewUrl) {
      setErrorMsg('Please capture a leaf photo, upload an image, or select a sample image first.');
      return;
    }

    setIsScanning(true);
    setErrorMsg(null);

    try {
      if (selectedFile) {
        const formData = new FormData();
        formData.append('file', selectedFile);
        if (selectedCrop) formData.append('crop_type', selectedCrop);

        const res = await fetch('/api/v1/predict/', {
          method: 'POST',
          body: formData
        });

        if (!res.ok) {
          const errorData = await res.json().catch(() => null);
          const detail = errorData && errorData.detail ? errorData.detail : `Server error (HTTP ${res.status})`;
          throw new Error(detail);
        }

        const data = await res.json();
        setIsScanning(false);
        setDiagnosisResult(data.prediction);
        if (onAnalyzeCompleted) onAnalyzeCompleted(data.prediction);
      } else {
        // Sample analysis fallback
        setIsScanning(false);
      }
    } catch (err) {
      console.error('API prediction error:', err);
      setIsScanning(false);
      setErrorMsg(err.message || 'Failed to complete leaf disease diagnosis. Please verify the backend server is running.');
    }
  };

  const resetScanner = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setDiagnosisResult(null);
    setErrorMsg(null);
    if (inputMode === 'camera') {
      startCameraStream();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="glass-panel p-6 rounded-2xl bg-gradient-to-r from-slate-900/90 via-slate-900/80 to-emerald-950/40 border-emerald-500/20">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-400" />
              <h2 className="text-xl font-bold text-white font-display">AI Crop Disease Diagnostics</h2>
            </div>
            <p className="text-xs text-slate-300">
              Powered by TensorFlow MobileNet Computer Vision. Upload leaf imagery to get instant diagnostic breakdown and treatment plans.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={selectedCrop}
              onChange={(e) => setSelectedCrop(e.target.value)}
              className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-xl px-3 py-2 focus:outline-none focus:border-emerald-500"
            >
              <option value="">Auto-Detect Crop Type</option>
              <option value="Tomato">Tomato</option>
              <option value="Potato">Potato</option>
              <option value="Corn">Corn (Maize)</option>
              <option value="Apple">Apple</option>
              <option value="Grape">Grape</option>
            </select>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Image Upload & Dropzone */}
        <div className="lg:col-span-5 space-y-4">
          <div className="glass-panel p-6 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                {inputMode === 'camera' ? (
                  <Camera className="w-4 h-4 text-emerald-400" />
                ) : (
                  <UploadCloud className="w-4 h-4 text-emerald-400" />
                )}
                Leaf Input Source
              </h3>

              {/* Mode Toggle: Live Camera (Primary/Default) vs Upload Photo */}
              <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
                <button
                  type="button"
                  onClick={() => handleModeChange('camera')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
                    inputMode === 'camera'
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Camera className="w-3.5 h-3.5" />
                  Live Camera
                </button>
                <button
                  type="button"
                  onClick={() => handleModeChange('upload')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
                    inputMode === 'upload'
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <UploadCloud className="w-3.5 h-3.5" />
                  Upload Photo
                </button>
              </div>
            </div>

            {/* Scan Container: Live Video Stream, Captured Preview, or Dropzone */}
            <div className="scan-container border-2 border-dashed border-slate-700 hover:border-emerald-500/50 rounded-2xl p-4 text-center transition-all bg-slate-950/50 relative overflow-hidden">
              {isScanning && <div className="scan-laser" />}

              {/* State 1: A photo is captured / selected / preview available */}
              {previewUrl ? (
                <div className="space-y-3">
                  <div className="relative">
                    <img
                      src={previewUrl}
                      alt="Leaf Sample Preview"
                      className="max-h-72 mx-auto rounded-xl object-cover shadow-lg border border-slate-800"
                    />
                    {selectedFile && (
                      <span className="absolute bottom-2 right-2 px-2.5 py-1 text-[10px] font-mono font-semibold rounded-md bg-slate-900/90 text-emerald-400 border border-emerald-500/30 backdrop-blur-sm">
                        Captured Frame Ready
                      </span>
                    )}
                  </div>
                  <div className="flex justify-center gap-3">
                    <button
                      type="button"
                      onClick={handleRetakePhoto}
                      className="text-xs px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-300 hover:text-emerald-400 hover:border-emerald-500/40 transition-all flex items-center gap-1.5"
                    >
                      <RefreshCw className="w-3.5 h-3.5" /> Retake / Restart Camera
                    </button>
                    <button
                      type="button"
                      onClick={resetScanner}
                      className="text-xs px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-rose-400 transition-all"
                    >
                      Clear
                    </button>
                  </div>
                </div>
              ) : inputMode === 'camera' ? (
                /* State 2: Live Camera Viewport */
                <div className="space-y-3">
                  <div className="relative rounded-xl overflow-hidden bg-slate-900 aspect-video max-h-72 flex items-center justify-center border border-slate-800">
                    {/* Live Video Feed */}
                    <video
                      ref={videoRef}
                      autoPlay
                      playsInline
                      muted
                      className="w-full h-full object-cover"
                    />

                    {/* Viewfinder Target Framing Overlay */}
                    <div className="absolute inset-4 pointer-events-none border border-emerald-500/30 rounded-lg flex flex-col justify-between p-2">
                      <div className="flex justify-between">
                        <span className="w-3 h-3 border-t-2 border-l-2 border-emerald-400" />
                        <span className="w-3 h-3 border-t-2 border-r-2 border-emerald-400" />
                      </div>
                      <div className="text-center">
                        <p className="text-[10px] text-emerald-300 font-mono tracking-wider bg-slate-950/70 px-2 py-0.5 rounded-full inline-block">
                          ALIGN LEAF WITHIN TARGET
                        </p>
                      </div>
                      <div className="flex justify-between">
                        <span className="w-3 h-3 border-b-2 border-l-2 border-emerald-400" />
                        <span className="w-3 h-3 border-b-2 border-r-2 border-emerald-400" />
                      </div>
                    </div>

                    {cameraLoading && (
                      <div className="absolute inset-0 bg-slate-950/80 flex flex-col items-center justify-center gap-2">
                        <RefreshCw className="w-6 h-6 text-emerald-400 animate-spin" />
                        <span className="text-xs text-slate-300 font-medium">Connecting to camera hardware...</span>
                      </div>
                    )}
                  </div>

                  {/* Hidden canvas for drawing frame and exporting Blob */}
                  <canvas ref={canvasRef} className="hidden" />

                  {/* Capture Button */}
                  <div className="flex justify-center">
                    <button
                      type="button"
                      onClick={handleCaptureLeaf}
                      disabled={cameraLoading}
                      className="btn btn-primary px-5 py-2.5 rounded-xl font-semibold text-xs flex items-center gap-2 shadow-lg shadow-emerald-500/20 disabled:opacity-50"
                    >
                      <Camera className="w-4 h-4" />
                      Capture Leaf
                    </button>
                  </div>
                </div>
              ) : (
                /* State 3: Upload Photo Dropzone */
                <label className="cursor-pointer space-y-3 block py-6">
                  <div className="w-14 h-14 mx-auto rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
                    <ScanLine className="w-7 h-7" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-200">
                      Click to upload leaf photo or drop image here
                    </p>
                    <p className="text-xs text-slate-500 mt-1">Supports JPG, PNG, WEBP (Max 10MB)</p>
                  </div>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </label>
              )}
            </div>

            {errorMsg && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Analyze Action Button */}
            <button
              onClick={handleUploadAndAnalyze}
              disabled={isScanning || (!selectedFile && !previewUrl)}
              className="w-full btn btn-primary py-3 font-semibold text-sm disabled:opacity-50"
            >
              {isScanning ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Analyzing Neural Patterns...
                </>
              ) : (
                <>
                  <FlaskConical className="w-4 h-4" />
                  Run AI Disease Analysis
                </>
              )}
            </button>
          </div>

          {/* Quick Demo Sample Picker */}
          <div className="glass-panel p-5 rounded-2xl space-y-3">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Or Select Demo Test Samples:
            </p>
            <div className="grid grid-cols-3 gap-2">
              {sampleLeafOptions.map((sample, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSelectSample(sample)}
                  className="p-2 rounded-xl bg-slate-900/80 hover:bg-slate-800 border border-slate-800 hover:border-emerald-500/40 text-left transition-all space-y-1.5"
                >
                  <img
                    src={sample.url}
                    alt={sample.name}
                    className="w-full h-14 object-cover rounded-lg"
                  />
                  <p className="text-[11px] font-medium text-slate-300 truncate">{sample.name}</p>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Diagnostic Results Card */}
        <div className="lg:col-span-7">
          {diagnosisResult ? (
            <div className="glass-panel p-6 rounded-2xl space-y-6 border-emerald-500/30">
              {/* Diagnosis Header */}
              <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800">
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`badge ${
                      diagnosisResult.status === 'Healthy' ? 'badge-emerald' : 'badge-rose'
                    }`}>
                      {diagnosisResult.status === 'Healthy' ? (
                        <CheckCircle className="w-3.5 h-3.5" />
                      ) : (
                        <ShieldAlert className="w-3.5 h-3.5" />
                      )}
                      {diagnosisResult.status}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      Confidence: <strong className="text-emerald-400">{diagnosisResult.confidence}%</strong>
                    </span>
                  </div>
                  <h3 className="text-2xl font-extrabold text-white font-display mt-1">
                    {diagnosisResult.crop} — {diagnosisResult.disease}
                  </h3>
                  <p className="text-xs text-slate-400 italic font-mono">{diagnosisResult.scientific_name}</p>
                </div>

                <div className="text-right">
                  <span className="text-[11px] text-slate-500 block">Severity Risk</span>
                  <span className={`text-sm font-bold ${
                    diagnosisResult.severity === 'Critical' ? 'text-rose-400' :
                    diagnosisResult.severity === 'High' ? 'text-amber-400' :
                    diagnosisResult.severity === 'Moderate' ? 'text-yellow-400' : 'text-emerald-400'
                  }`}>
                    {diagnosisResult.severity}
                  </span>
                </div>
              </div>

              {/* Actionable Agronomic Recommendation Box */}
              <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-500/30 space-y-2">
                <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wide flex items-center gap-1.5">
                  <Sprout className="w-4 h-4" /> Immediate Treatment Action
                </h4>
                <p className="text-sm text-slate-200 font-medium leading-relaxed">
                  {diagnosisResult.recommendation}
                </p>
              </div>

              {/* Symptoms & Causes Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> Observed Symptoms
                  </h4>
                  <ul className="space-y-1.5 text-xs text-slate-300 list-disc list-inside">
                    {diagnosisResult.symptoms.map((symptom, sIdx) => (
                      <li key={sIdx}>{symptom}</li>
                    ))}
                  </ul>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Environmental Causes
                  </h4>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {diagnosisResult.causes}
                  </p>
                </div>
              </div>

              {/* Organic vs Chemical Remedies Tabs */}
              <div className="space-y-3">
                <h4 className="text-sm font-bold text-white font-display">Management & Treatment Protocol</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-slate-900/80 border border-emerald-500/20 space-y-2">
                    <span className="badge badge-emerald text-[10px]">Organic Treatment</span>
                    <ul className="space-y-1 text-xs text-slate-300 list-disc list-inside pt-1">
                      {diagnosisResult.organic_remedies.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-900/80 border border-blue-500/20 space-y-2">
                    <span className="badge badge-blue text-[10px]">Chemical Control</span>
                    <ul className="space-y-1 text-xs text-slate-300 list-disc list-inside pt-1">
                      {diagnosisResult.chemical_remedies.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="glass-panel p-12 text-center rounded-2xl flex flex-col items-center justify-center space-y-4 h-full min-h-[420px]">
              <div className="w-16 h-16 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500">
                <FileCheck className="w-8 h-8 text-emerald-500/50" />
              </div>
              <div className="max-w-md space-y-1">
                <h3 className="text-lg font-bold text-white font-display">Awaiting Leaf Scanner Input</h3>
                <p className="text-xs text-slate-400">
                  Upload a clear image of a crop leaf or choose a demo sample to view real-time AI diagnosis and remedy instructions.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
