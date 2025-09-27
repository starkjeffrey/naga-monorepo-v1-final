/**
 * StudentPhoto Component
 *
 * A specialized component for handling student photos with:
 * - Photo upload and capture
 * - Image editing capabilities
 * - Fallback handling
 * - OCR integration for document photos
 * - Security compliance
 */

import React, { useState, useRef, useCallback } from 'react';
import { Upload, Avatar, Button, Modal, Space, message, Spin, Image } from 'antd';
import {
  UserOutlined,
  CameraOutlined,
  UploadOutlined,
  EditOutlined,
  DeleteOutlined,
  ScanOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd/es/upload';
import type { Student } from '../types/Student';

interface StudentPhotoProps {
  student?: Student;
  photoUrl?: string;
  size?: number | 'small' | 'default' | 'large';
  editable?: boolean;
  showCamera?: boolean;
  showOCR?: boolean;
  onPhotoChange?: (file: File, url: string) => void;
  onPhotoDelete?: () => void;
  onOCRScan?: (file: File) => void;
  className?: string;
}

const StudentPhoto: React.FC<StudentPhotoProps> = ({
  student,
  photoUrl,
  size = 'default',
  editable = false,
  showCamera = false,
  showOCR = false,
  onPhotoChange,
  onPhotoDelete,
  onOCRScan,
  className,
}) => {
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const currentPhotoUrl = photoUrl || student?.photoUrl;

  // Handle photo upload
  const handleUpload: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError } = options;

    try {
      setUploading(true);
      const fileObj = file as File;

      // Validate file type and size
      if (!fileObj.type.startsWith('image/')) {
        message.error('Please upload an image file');
        onError?.(new Error('Invalid file type'));
        return;
      }

      if (fileObj.size > 5 * 1024 * 1024) { // 5MB limit
        message.error('Image size must be less than 5MB');
        onError?.(new Error('File too large'));
        return;
      }

      // Create preview URL
      const url = URL.createObjectURL(fileObj);
      setPreviewUrl(url);

      // Call parent callback
      onPhotoChange?.(fileObj, url);
      onSuccess?.(fileObj);
      message.success('Photo uploaded successfully');

    } catch (error) {
      console.error('Upload error:', error);
      message.error('Failed to upload photo');
      onError?.(error as Error);
    } finally {
      setUploading(false);
    }
  };

  // Start camera capture
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        }
      });
      setCameraStream(stream);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (error) {
      console.error('Camera error:', error);
      message.error('Unable to access camera');
    }
  };

  // Stop camera
  const stopCamera = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      setCameraStream(null);
    }
  };

  // Capture photo from camera
  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const video = videoRef.current;
    const context = canvas.getContext('2d');

    if (!context) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0);

    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], 'camera-capture.jpg', { type: 'image/jpeg' });
        const url = URL.createObjectURL(blob);
        setPreviewUrl(url);
        onPhotoChange?.(file, url);
        stopCamera();
        setIsModalVisible(false);
        message.success('Photo captured successfully');
      }
    }, 'image/jpeg', 0.8);
  };

  // Handle photo deletion
  const handleDelete = () => {
    Modal.confirm({
      title: 'Delete Photo',
      content: 'Are you sure you want to delete this photo?',
      okText: 'Delete',
      okType: 'danger',
      onOk: () => {
        setPreviewUrl(null);
        onPhotoDelete?.();
        message.success('Photo deleted successfully');
      },
    });
  };

  // Handle OCR scan
  const handleOCRScan = (file: File) => {
    onOCRScan?.(file);
    message.info('Processing document for OCR...');
  };

  const uploadButton = (
    <div className="text-center">
      {uploading ? <Spin /> : <UploadOutlined />}
      <div style={{ marginTop: 8 }}>Upload</div>
    </div>
  );

  const cameraButton = (
    <Button
      icon={<CameraOutlined />}
      onClick={() => {
        setIsModalVisible(true);
        startCamera();
      }}
    >
      Camera
    </Button>
  );

  const editButtons = editable && (
    <div className="student-photo-actions">
      <Space>
        <Upload
          name="photo"
          listType="picture"
          showUploadList={false}
          customRequest={handleUpload}
          accept="image/*"
        >
          <Button icon={<UploadOutlined />} size="small">
            Upload
          </Button>
        </Upload>

        {showCamera && (
          <Button
            icon={<CameraOutlined />}
            size="small"
            onClick={() => {
              setIsModalVisible(true);
              startCamera();
            }}
          >
            Camera
          </Button>
        )}

        {showOCR && (
          <Upload
            name="document"
            listType="picture"
            showUploadList={false}
            customRequest={(options) => {
              const file = options.file as File;
              handleOCRScan(file);
            }}
            accept="image/*"
          >
            <Button icon={<ScanOutlined />} size="small">
              OCR Scan
            </Button>
          </Upload>
        )}

        {currentPhotoUrl && (
          <Button
            icon={<DeleteOutlined />}
            size="small"
            danger
            onClick={handleDelete}
          >
            Delete
          </Button>
        )}
      </Space>
    </div>
  );

  return (
    <div className={`student-photo ${className || ''}`}>
      <div className="relative inline-block">
        <Avatar
          size={size}
          src={previewUrl || currentPhotoUrl}
          icon={<UserOutlined />}
          className="shadow-md"
        />

        {currentPhotoUrl && (
          <Button
            size="small"
            icon={<EyeOutlined />}
            className="absolute top-0 right-0 rounded-full shadow-md"
            onClick={() => {
              Modal.info({
                title: student ? `${student.fullName} - Photo` : 'Student Photo',
                content: (
                  <div className="text-center">
                    <Image
                      src={previewUrl || currentPhotoUrl}
                      alt="Student photo"
                      style={{ maxWidth: '100%', maxHeight: '400px' }}
                    />
                  </div>
                ),
                width: 600,
              });
            }}
          />
        )}
      </div>

      {editButtons}

      {/* Camera Modal */}
      <Modal
        title="Capture Photo"
        open={isModalVisible}
        onCancel={() => {
          stopCamera();
          setIsModalVisible(false);
        }}
        footer={[
          <Button
            key="cancel"
            onClick={() => {
              stopCamera();
              setIsModalVisible(false);
            }}
          >
            Cancel
          </Button>,
          <Button
            key="capture"
            type="primary"
            icon={<CameraOutlined />}
            onClick={capturePhoto}
            disabled={!cameraStream}
          >
            Capture
          </Button>,
        ]}
        width={720}
      >
        <div className="text-center">
          <video
            ref={videoRef}
            autoPlay
            muted
            className="border rounded-lg"
            style={{ maxWidth: '100%', height: '360px' }}
          />
          <canvas ref={canvasRef} style={{ display: 'none' }} />
        </div>
      </Modal>
    </div>
  );
};

export default StudentPhoto;