import base64
import io
import json
import os
from app.services.embedding_service import get_embedding_by_id, insert_new_embedding, verification_identity, verification_All
from keras_facenet import FaceNet
from ultralytics import YOLO
import joblib
import cv2
import numpy as np
from scipy.spatial.distance import cosine
from sqlalchemy.orm import Session
import logging
import time
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger("uvicorn.error")

current_file = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file)

class FaceRecognitionSystem:
    def __init__(self):
        """Initialize với enhanced configuration"""
        # Load models
        model_file = os.path.join(current_dir, "..", "assets", "yolov11n-face.pt")
        svm_file = os.path.join(current_dir, "..", "assets", "svm_facenet_18.pkl")

        self.face_detector = YOLO(model_file) # phát hiện khuôn mặt
        self.embedder = FaceNet() # trích xuất embedding
        self.svm_model = joblib.load(svm_file) # phân loại ai là ai (dựa trên embedding)
        
        # Thresholds với fine-tuning
        self.verification_threshold = 0.55
        self.svm_confidence_threshold = 0.8 #0.7
        self.min_face_size = 80  # Minimum face size in pixels
        self.face_confidence_threshold = 0.5
        
        # Performance monitoring
        self.metrics = {
            'preprocessing_time': [],
            'embedding_time': [],
            'svm_time': [],
            'verification_time': []
        }
        
        # Embedding normalization cache
        self._embedding_norm_cache = {}
        
    def preprocess_face(self, face_img: np.ndarray) -> Optional[np.ndarray]:
        """EXACT replication của training pipeline preprocessing"""
        try:
            # CRITICAL: Match EXACTLY với training pipeline
            # KHÔNG convert color space
            # KHÔNG normalize
            # CHỈ resize và convert dtype
            
            face = cv2.resize(face_img, (160, 160))
            return face.astype("float32")
            
        except Exception as e:
            logger.error(f"Face preprocessing failed: {e}")
            return None
    
    def detect_faces(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Enhanced face detection với quality filtering"""
        try:
            start_time = time.time()
            
            # Validate input
            if image is None or not isinstance(image, np.ndarray):
                raise ValueError("Invalid image input")
            
            # Run YOLO detection
            detections = self.face_detector(image, verbose=False)[0]
            faces = []
            
            if detections.boxes is None:
                return faces
            
            for box in detections.boxes:
                # Extract coordinates safely
                coords = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = map(int, coords)
                confidence = float(box.conf[0].cpu().numpy())
                
                # Skip low confidence detections
                if confidence < self.face_confidence_threshold:
                    continue
                
                # Validate bounding box
                if x2 <= x1 or y2 <= y1:
                    continue
                
                # Clamp coordinates to image bounds
                h, w = image.shape[:2]
                x1 = max(0, min(x1, w-1))
                y1 = max(0, min(y1, h-1))
                x2 = max(x1+1, min(x2, w))
                y2 = max(y1+1, min(y2, h))
                
                # Check minimum face size
                face_width = x2 - x1
                face_height = y2 - y1
                if face_width < self.min_face_size or face_height < self.min_face_size:
                    logger.debug(f"Face too small: {face_width}x{face_height}")
                    continue
                
                # Extract face ROI with padding for better alignment
                padding = int(min(face_width, face_height) * 0.1)
                x1_pad = max(0, x1 - padding)
                y1_pad = max(0, y1 - padding)
                x2_pad = min(w, x2 + padding)
                y2_pad = min(h, y2 + padding)
                
                face_roi = image[y1_pad:y2_pad, x1_pad:x2_pad]
                
                # Skip invalid ROIs
                if face_roi.size == 0:
                    continue
                
                # Calculate face quality metrics
                brightness = np.mean(face_roi)
                contrast = np.std(face_roi)
                
                faces.append({
                    'bbox': (x1, y1, x2, y2),
                    'bbox_padded': (x1_pad, y1_pad, x2_pad, y2_pad),
                    'confidence': confidence,
                    'face_image': face_roi,
                    'quality_metrics': {
                        'brightness': brightness,
                        'contrast': contrast,
                        'size': (face_width, face_height)
                    }
                })
            
            detection_time = time.time() - start_time
            logger.debug(f"Detected {len(faces)} faces in {detection_time:.3f}s")
            
            # Sort by confidence
            faces.sort(key=lambda x: x['confidence'], reverse=True)
            
            return faces
            
        except Exception as e:
            logger.error(f"Face detection error: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def extract_embedding(self, face_image: np.ndarray) -> Optional[np.ndarray]:
        """Extract embedding với EXACT training pipeline compatibility"""
        try:
            #start_time = time.time()
            
            # CRITICAL: Use exact same preprocessing as training
            processed = self.preprocess_face(face_image)
            if processed is None:
                return None
            
            # Log để verify preprocessing output
            logger.debug(f"Preprocessed face stats: shape={processed.shape}, "
                        f"dtype={processed.dtype}, "
                        f"range=[{processed.min():.1f}, {processed.max():.1f}]")
            
            # Extract embedding - KHÔNG batch dimension optimization
            embedding = self.embedder.embeddings(np.expand_dims(processed, axis=0))[0]
            
            # CRITICAL: Check embedding characteristics
            embedding_norm = np.linalg.norm(embedding)
            logger.debug(f"Raw embedding norm: {embedding_norm:.4f}")
            
            # Validate embedding
            if np.all(embedding == 0) or np.isnan(embedding).any() or np.isinf(embedding).any():
                logger.error("Invalid embedding detected (zeros/nan/inf)")
                return None
            
            # IMPORTANT: Normalize embedding để ensure consistent similarity
            # nhưng phải check xem training có normalize không
            if embedding_norm > 0:
                embedding_normalized = embedding / embedding_norm
                
                # Log both versions để debug
                logger.debug(f"Normalized embedding: norm={np.linalg.norm(embedding_normalized):.4f}")
                
                # Return normalized version
                return embedding_normalized
            else:
                logger.error("Zero norm embedding")
                return None
            
        except Exception as e:
            logger.error(f"Embedding extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Enhanced similarity calculation với multiple metrics"""
        try:
            # Check if embeddings are already normalized
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                logger.warning("Zero norm embedding in similarity calculation")
                return 0.0
            
            # CRITICAL: Only normalize if NOT already normalized
            # Avoid double normalization issue
            if abs(norm1 - 1.0) > 1e-3:  # Use larger epsilon for float precision
                logger.debug(f"Normalizing embedding1: norm={norm1:.6f}")
                embedding1 = embedding1 / norm1
            
            if abs(norm2 - 1.0) > 1e-3:
                logger.debug(f"Normalizing embedding2: norm={norm2:.6f}")
                embedding2 = embedding2 / norm2
            
            # Method 1: Cosine similarity via scipy
            cosine_sim = 1 - cosine(embedding1, embedding2)
            
            # Method 2: Direct dot product (for validation)
            dot_sim = np.dot(embedding1, embedding2)
            
            # Log if there's significant difference
            if abs(cosine_sim - dot_sim) > 1e-4:
                logger.warning(f"Similarity mismatch: cosine={cosine_sim:.6f}, dot={dot_sim:.6f}")
            
            return float(cosine_sim)
            
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return 0.0
    
    def authenticate_face(self, db: Session, image: np.ndarray) -> Dict[str, Any]:
        """authentication với comprehensive"""
        try:
            start_time = time.time()
            
            # Input validation và logging
            logger.info(f"Authentication started - Image shape: {image.shape}, dtype: {image.dtype}")
            
            # Detect faces
            faces = self.detect_faces(image)
            logger.info(f"Detected {len(faces)} face(s)")
            
            if len(faces) == 0:
                return {"success": False, "message": "No face detected"}
            
            best_match = None
            best_verification_score = 0
            all_results = []  # Store all results for debugging
            
            for idx, face_data in enumerate(faces):
                face_result = {
                    'face_idx': idx,
                    'detection_confidence': face_data['confidence'],
                    'quality_metrics': face_data['quality_metrics']
                }
                
                # Extract embedding
                embedding_start = time.time()
                current_embedding = self.extract_embedding(face_data['face_image'])
                embedding_time = time.time() - embedding_start
                
                if current_embedding is None:
                    logger.warning(f"Failed to extract embedding for face {idx}")
                    face_result['embedding_status'] = 'failed'
                    all_results.append(face_result)
                    continue
                
                face_result['embedding_status'] = 'success'
                face_result['embedding_time'] = embedding_time
                
                # Log embedding stats
                logger.debug(f"Face {idx} embedding: norm={np.linalg.norm(current_embedding):.4f}, "
                            f"mean={current_embedding.mean():.4f}, std={current_embedding.std():.4f}")
                
                # Stage 1: SVM Classification
                svm_start = time.time()
                predicted_label = None
                svm_confidence = 0.0
                
                try:
                    # Ensure correct shape for SVM
                    embedding_for_svm = current_embedding.reshape(1, -1)
                    
                    svm_predictions = self.svm_model.predict(embedding_for_svm)
                    svm_probabilities = self.svm_model.predict_proba(embedding_for_svm)[0]
                    
                    predicted_label = svm_predictions[0]
                    svm_confidence = float(svm_probabilities.max())
                    
                    # Get top 3 predictions for debugging
                    top_indices = np.argsort(svm_probabilities)[-3:][::-1]
                    top_predictions = [(self.svm_model.classes_[i], svm_probabilities[i]) 
                                     for i in top_indices]
                    
                    logger.info(f"SVM Top 3: {top_predictions}")
                    
                    # Filter low-confidence predictions
                    if svm_confidence < self.svm_confidence_threshold:
                        logger.debug(f"SVM confidence too low: {svm_confidence:.3f}")
                        predicted_label = None
                        
                except Exception as e:
                    logger.error(f"SVM prediction failed: {e}")
                    import traceback
                    traceback.print_exc()
                
                svm_time = time.time() - svm_start
                face_result['svm_prediction'] = predicted_label
                face_result['svm_confidence'] = svm_confidence
                face_result['svm_time'] = svm_time
                
                # Stage 2: Embedding Verification
                verification_start = time.time()
                
                if predicted_label:
                    # Focused verification
                    registered_faces = verification_identity(db, predicted_label)
                    logger.info(f"Checking {len(registered_faces)} faces for identity: {predicted_label}")
                else:
                    # Fallback to all faces
                    registered_faces = verification_All(db)
                    logger.info(f"Checking all {len(registered_faces)} registered faces")
                
                if not registered_faces:
                    logger.warning("No registered faces found in database")
                    face_result['verification_status'] = 'no_candidates'
                    all_results.append(face_result)
                    continue
                
                # Find best embedding match
                best_embedding_similarity = 0
                best_candidate = None
                similarity_scores = []
               
                for ho_ten, embedding_json, ma_so, danh_gia in registered_faces:
                    try:
                        stored_embedding = np.array(json.loads(embedding_json))
                        
                        # Validate stored embedding
                        if stored_embedding.shape != current_embedding.shape:
                            logger.error(f"Shape mismatch for {ho_ten}: "
                                       f"stored={stored_embedding.shape}, current={current_embedding.shape}")
                            continue
                        
                        similarity = self.calculate_similarity(current_embedding, stored_embedding)
                        similarity_scores.append((ho_ten, similarity))
                        
                        if similarity > best_embedding_similarity:
                            best_embedding_similarity = similarity
                            best_candidate = {
                                "username": ho_ten,
                                "user_id": ma_so,
                                "embedding_similarity": similarity,
                                "detection_confidence": face_data['confidence'],
                                "svm_prediction": predicted_label if predicted_label else "Unknown",
                                "svm_confidence": svm_confidence,
                                "quality_score": danh_gia
                            }
                            
                    except Exception as e:
                        logger.error(f"Error processing {ho_ten}: {e}")
                        continue
                
                verification_time = time.time() - verification_start
                face_result['verification_time'] = verification_time
                
                # Log top matches
                similarity_scores.sort(key=lambda x: x[1], reverse=True)
                logger.info(f"Top 5 similarity scores: {similarity_scores[:5]}")
                face_result['top_matches'] = similarity_scores[:5]
                
                # Decision Logic
                if best_candidate and best_embedding_similarity > self.verification_threshold:
                    
                    # Calculate final verification score
                    if predicted_label and predicted_label == best_candidate["user_id"]:
                        # Perfect match
                        verification_score = (svm_confidence + best_embedding_similarity) / 2
                        face_result['match_type'] = 'perfect'
                    elif not predicted_label:
                        # SVM failed but embedding matched
                        verification_score = best_embedding_similarity * 0.8
                        face_result['match_type'] = 'embedding_only'
                    else:
                        # Mismatch between SVM and embedding
                        logger.warning(f"Identity mismatch: SVM={predicted_label}, "
                                     f"Embedding={best_candidate['username']}")
                        verification_score = best_embedding_similarity * 0.6
                        face_result['match_type'] = 'mismatch'
                    
                    if verification_score > best_verification_score:
                        best_verification_score = verification_score
                        best_match = best_candidate
                        best_match["final_score"] = verification_score
                        best_match["match_details"] = face_result
                
                all_results.append(face_result)
            
            # Calculate total processing time
            total_time = time.time() - start_time
         
            # Final decision
            if best_match and best_verification_score > self.verification_threshold:
                return {
                    "success": True,
                    "message": "Authentication successful",
                    "authentication_details": {
                        "svm_stage": best_match["svm_confidence"],
                        "verification_stage": best_match['embedding_similarity'],
                        "final_score": best_match['final_score'],
                        "pipeline": "2-stage: SVM Classification + Embedding Verification",
                        "processing_time": f"{total_time:.3f}s",
                        "faces_processed": len(faces)
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Face not recognized or confidence too low",
                    "debug_info": {
                        "best_similarity": best_verification_score,
                        "threshold": self.verification_threshold,
                        "svm_threshold": self.svm_confidence_threshold,
                        "processing_time": f"{total_time:.3f}s",
                        "faces_detected": len(faces),
                        "all_results": all_results  # Detailed debug info
                    }
                }
                
        except Exception as e:
            logger.error(f"Authentication failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Authentication error: {str(e)}"
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get average performance metrics"""
        metrics = {}
        for key, values in self.metrics.items():
            if values:
                metrics[key] = {
                    'avg': np.mean(values),
                    'min': np.min(values),
                    'max': np.max(values),
                    'count': len(values)
                }
        return metrics
    
    
    def register_face(self, maso: str, image: np.ndarray, db: Session):
        """Register a new face with both SVM classification and embedding storage"""
        # Detect faces
        faces = self.detect_faces(image)
        
        if len(faces) == 0:
            return {"success": False, "message": "No face detected"}
        
        if len(faces) > 1:
            return {"success": False, "message": "Multiple faces detected. Please ensure only one face is visible"}
        
        face_data = faces[0]
        
        # Extract embedding với SAME normalization as authentication
        embedding = self.extract_embedding(face_data['face_image'])
        if embedding is None:
            return {"success": False, "message": "Failed to extract face features"}
        
        # CRITICAL: Ensure embedding is L2 normalized before ANY usage
        embedding_norm = np.linalg.norm(embedding)
        if embedding_norm > 0:
            embedding = embedding / embedding_norm
        
        logger.info(f"Registration embedding: norm={np.linalg.norm(embedding):.4f}, "
                   f"mean={embedding.mean():.4f}, std={embedding.std():.4f}")
        
        # Step 1: SVM Classification for identity prediction
        # try:
        #     svm_prediction = self.svm_model.predict([embedding])[0]
        #     svm_confidence = self.svm_model.predict_proba([embedding])[0].max()
            
        #     # If SVM predicts existing identity with high confidence, suggest verification
        #     if svm_confidence > self.svm_confidence_threshold:
        #         return {
        #             "success": False, 
        #             "message": f"Face matches existing identity: {svm_prediction} (confidence: {svm_confidence:.2f}). Use authentication instead.",
        #             "suggested_identity": svm_prediction,
        #             "svm_confidence": svm_confidence
        #         }
        # except Exception as e:
        #     # If SVM fails (new person not in training set), proceed with registration
        #     logger.warning(f"SVM prediction failed (new person): {e}")
        
        # Step 2: Check database for similar embeddings
        existing_embeddings = get_embedding_by_id(db, maso)
        if existing_embeddings:                   
            # Verify against existing embeddings
            for (embedding_json,) in existing_embeddings:
                stored_embedding = np.array(json.loads(embedding_json))
                
                # CRITICAL: Normalize stored embedding too
                stored_norm = np.linalg.norm(stored_embedding)
                if stored_norm > 0:
                    stored_embedding = stored_embedding / stored_norm
                
                similarity = self.calculate_similarity(embedding, stored_embedding)
                logger.debug(f"Checking existing embedding: similarity={similarity:.4f}")
                
                if similarity > self.verification_threshold:
                    return {
                        "success": False,
                        "message": f"Face already registered for user {maso} (similarity: {similarity:.2f})"
                    }
        
        # Step 3: Save NORMALIZED embedding
        embedding_json = json.dumps(embedding.tolist())
        insert_new_embedding(db, maso, embedding_json, face_data['confidence'])
        
        logger.info(f"Successfully registered face for {maso}")
        
        return {
            "success": True, 
            "message": "Face registered successfully",
            "maso": maso,
            "quality_score": face_data['confidence'],
            "embedding_stats": {
                "norm": float(np.linalg.norm(embedding)),
                "dimensions": embedding.shape[0]
            },
            "note": "Face will be included in future SVM retraining"
        }