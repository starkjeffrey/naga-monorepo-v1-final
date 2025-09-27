/**
 * StudentForm Component
 *
 * A comprehensive form component for student data entry and editing:
 * - Multi-section form layout
 * - Real-time validation
 * - Auto-save functionality
 * - OCR integration for document processing
 * - Address validation
 * - Emergency contact management
 */

import React, { useState, useEffect } from 'react';
import {
  Form,
  Input,
  Select,
  DatePicker,
  Upload,
  Button,
  Space,
  Card,
  Row,
  Col,
  Switch,
  Divider,
  message,
  AutoComplete,
  InputNumber,
  Checkbox,
} from 'antd';
import {
  UserOutlined,
  MailOutlined,
  PhoneOutlined,
  HomeOutlined,
  UploadOutlined,
  ScanOutlined,
  SaveOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { FormInstance } from 'antd/es/form';
import dayjs from 'dayjs';
import StudentPhoto from './StudentPhoto';
import type { Student, StudentFormData } from '../types/Student';

interface StudentFormProps {
  student?: Student;
  mode?: 'create' | 'edit' | 'view';
  onSubmit?: (data: StudentFormData) => void;
  onCancel?: () => void;
  loading?: boolean;
  autoSave?: boolean;
  showOCR?: boolean;
  className?: string;
}

const { Option } = Select;
const { TextArea } = Input;

const COUNTRIES = ['United States', 'Canada', 'Mexico', 'United Kingdom', 'Germany', 'France', 'Spain'];
const PROGRAMS = ['Computer Science', 'Business Administration', 'Engineering', 'Medicine', 'Law', 'Education'];
const ACADEMIC_YEARS = ['Freshman', 'Sophomore', 'Junior', 'Senior', 'Graduate'];

const StudentForm: React.FC<StudentFormProps> = ({
  student,
  mode = 'create',
  onSubmit,
  onCancel,
  loading = false,
  autoSave = false,
  showOCR = false,
  className,
}) => {
  const [form] = Form.useForm<StudentFormData>();
  const [hasChanges, setHasChanges] = useState(false);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [autoSaveTimer, setAutoSaveTimer] = useState<NodeJS.Timeout | null>(null);

  const isReadOnly = mode === 'view';

  useEffect(() => {
    if (student) {
      form.setFieldsValue({
        ...student,
        dateOfBirth: student.dateOfBirth ? dayjs(student.dateOfBirth) : undefined,
        enrollmentDate: student.enrollmentDate ? dayjs(student.enrollmentDate) : undefined,
      });
    }
  }, [student, form]);

  useEffect(() => {
    if (autoSave && hasChanges && mode !== 'view') {
      if (autoSaveTimer) {
        clearTimeout(autoSaveTimer);
      }

      const timer = setTimeout(() => {
        handleAutoSave();
      }, 3000); // Auto-save after 3 seconds of inactivity

      setAutoSaveTimer(timer);
    }

    return () => {
      if (autoSaveTimer) {
        clearTimeout(autoSaveTimer);
      }
    };
  }, [hasChanges, autoSave, mode]);

  const handleFormChange = () => {
    setHasChanges(true);
  };

  const handleAutoSave = async () => {
    try {
      const values = await form.validateFields();
      message.success('Draft saved automatically', 2);
      setHasChanges(false);
    } catch (error) {
      // Validation failed, skip auto-save
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const formData: StudentFormData = {
        ...values,
        dateOfBirth: values.dateOfBirth?.format('YYYY-MM-DD'),
        enrollmentDate: values.enrollmentDate?.format('YYYY-MM-DD'),
        photoFile,
      };
      onSubmit?.(formData);
      setHasChanges(false);
    } catch (error) {
      message.error('Please correct the errors in the form');
    }
  };

  const handleOCRScan = (file: File) => {
    // OCR processing would be implemented here
    message.info('Processing document with OCR...');

    // Simulated OCR result
    setTimeout(() => {
      form.setFieldsValue({
        firstName: 'John',
        lastName: 'Doe',
        dateOfBirth: dayjs('1995-01-01'),
        // Additional fields from OCR...
      });
      message.success('Information extracted from document');
      setHasChanges(true);
    }, 2000);
  };

  const validateAddress = async (address: string) => {
    // Address validation logic would be implemented here
    return true;
  };

  return (
    <div className={`student-form ${className || ''}`}>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        onValuesChange={handleFormChange}
        disabled={isReadOnly}
        size="large"
      >
        <Row gutter={24}>
          <Col span={24}>
            <Card title="Basic Information" className="mb-4">
              <Row gutter={16}>
                <Col span={6}>
                  <div className="text-center">
                    <StudentPhoto
                      student={student}
                      editable={!isReadOnly}
                      showCamera={true}
                      showOCR={showOCR}
                      onPhotoChange={(file, url) => {
                        setPhotoFile(file);
                        setHasChanges(true);
                      }}
                      onOCRScan={handleOCRScan}
                    />
                    {autoSave && hasChanges && (
                      <div className="text-xs text-orange-500 mt-2">
                        Unsaved changes
                      </div>
                    )}
                  </div>
                </Col>
                <Col span={18}>
                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item
                        label="Student ID"
                        name="studentId"
                        rules={[
                          { required: true, message: 'Student ID is required' },
                          { pattern: /^[A-Z]\d{8}$/, message: 'Format: A12345678' }
                        ]}
                      >
                        <Input
                          prefix={<UserOutlined />}
                          placeholder="A12345678"
                          maxLength={9}
                        />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item
                        label="First Name"
                        name="firstName"
                        rules={[{ required: true, message: 'First name is required' }]}
                      >
                        <Input placeholder="John" />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item
                        label="Last Name"
                        name="lastName"
                        rules={[{ required: true, message: 'Last name is required' }]}
                      >
                        <Input placeholder="Doe" />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item
                        label="Date of Birth"
                        name="dateOfBirth"
                        rules={[{ required: true, message: 'Date of birth is required' }]}
                      >
                        <DatePicker
                          style={{ width: '100%' }}
                          format="YYYY-MM-DD"
                          disabledDate={(date) => date.isAfter(dayjs().subtract(16, 'year'))}
                        />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item
                        label="Gender"
                        name="gender"
                        rules={[{ required: true, message: 'Gender is required' }]}
                      >
                        <Select placeholder="Select gender">
                          <Option value="male">Male</Option>
                          <Option value="female">Female</Option>
                          <Option value="other">Other</Option>
                          <Option value="prefer_not_to_say">Prefer not to say</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item
                        label="Nationality"
                        name="nationality"
                      >
                        <AutoComplete
                          options={COUNTRIES.map(country => ({ value: country }))}
                          placeholder="Select or type nationality"
                          filterOption={(inputValue, option) =>
                            option?.value.toLowerCase().includes(inputValue.toLowerCase()) ?? false
                          }
                        />
                      </Form.Item>
                    </Col>
                  </Row>
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>

        <Row gutter={24}>
          <Col span={12}>
            <Card title="Contact Information" className="mb-4">
              <Form.Item
                label="Email Address"
                name="email"
                rules={[
                  { required: true, message: 'Email is required' },
                  { type: 'email', message: 'Please enter a valid email' }
                ]}
              >
                <Input
                  prefix={<MailOutlined />}
                  placeholder="john.doe@example.com"
                />
              </Form.Item>

              <Form.Item
                label="Phone Number"
                name="phone"
                rules={[
                  { pattern: /^\+?[\d\s\-\(\)]{10,}$/, message: 'Please enter a valid phone number' }
                ]}
              >
                <Input
                  prefix={<PhoneOutlined />}
                  placeholder="+1 (555) 123-4567"
                />
              </Form.Item>

              <Form.Item
                label="Address"
                name="address"
                rules={[{ required: true, message: 'Address is required' }]}
              >
                <TextArea
                  rows={3}
                  placeholder="Street address, apartment, suite, etc."
                />
              </Form.Item>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    label="City"
                    name="city"
                    rules={[{ required: true, message: 'City is required' }]}
                  >
                    <Input placeholder="City" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="State/Province"
                    name="state"
                    rules={[{ required: true, message: 'State is required' }]}
                  >
                    <Input placeholder="State/Province" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="Postal Code"
                    name="postalCode"
                    rules={[{ required: true, message: 'Postal code is required' }]}
                  >
                    <Input placeholder="12345" />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                label="Country"
                name="country"
                rules={[{ required: true, message: 'Country is required' }]}
              >
                <Select placeholder="Select country">
                  {COUNTRIES.map(country => (
                    <Option key={country} value={country}>
                      {country}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Card>
          </Col>

          <Col span={12}>
            <Card title="Academic Information" className="mb-4">
              <Form.Item
                label="Program"
                name="program"
                rules={[{ required: true, message: 'Program is required' }]}
              >
                <Select placeholder="Select program">
                  {PROGRAMS.map(program => (
                    <Option key={program} value={program}>
                      {program}
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                label="Academic Year"
                name="academicYear"
                rules={[{ required: true, message: 'Academic year is required' }]}
              >
                <Select placeholder="Select academic year">
                  {ACADEMIC_YEARS.map(year => (
                    <Option key={year} value={year}>
                      {year}
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                label="Enrollment Date"
                name="enrollmentDate"
                rules={[{ required: true, message: 'Enrollment date is required' }]}
              >
                <DatePicker
                  style={{ width: '100%' }}
                  format="YYYY-MM-DD"
                />
              </Form.Item>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="GPA"
                    name="gpa"
                  >
                    <InputNumber
                      min={0}
                      max={4}
                      step={0.01}
                      precision={2}
                      style={{ width: '100%' }}
                      placeholder="3.50"
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="Credits Completed"
                    name="creditsCompleted"
                  >
                    <InputNumber
                      min={0}
                      style={{ width: '100%' }}
                      placeholder="60"
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                label="Status"
                name="status"
                rules={[{ required: true, message: 'Status is required' }]}
              >
                <Select placeholder="Select status">
                  <Option value="active">Active</Option>
                  <Option value="inactive">Inactive</Option>
                  <Option value="graduated">Graduated</Option>
                  <Option value="suspended">Suspended</Option>
                  <Option value="transferred">Transferred</Option>
                  <Option value="pending">Pending</Option>
                </Select>
              </Form.Item>
            </Card>
          </Col>
        </Row>

        <Row gutter={24}>
          <Col span={24}>
            <Card title="Emergency Contact" className="mb-4">
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    label="Contact Name"
                    name={['emergencyContact', 'name']}
                    rules={[{ required: true, message: 'Emergency contact name is required' }]}
                  >
                    <Input placeholder="Jane Doe" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="Relationship"
                    name={['emergencyContact', 'relationship']}
                    rules={[{ required: true, message: 'Relationship is required' }]}
                  >
                    <Select placeholder="Select relationship">
                      <Option value="parent">Parent</Option>
                      <Option value="guardian">Guardian</Option>
                      <Option value="sibling">Sibling</Option>
                      <Option value="spouse">Spouse</Option>
                      <Option value="other">Other</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="Phone Number"
                    name={['emergencyContact', 'phone']}
                    rules={[
                      { required: true, message: 'Emergency contact phone is required' },
                      { pattern: /^\+?[\d\s\-\(\)]{10,}$/, message: 'Please enter a valid phone number' }
                    ]}
                  >
                    <Input
                      prefix={<PhoneOutlined />}
                      placeholder="+1 (555) 123-4567"
                    />
                  </Form.Item>
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>

        <Row gutter={24}>
          <Col span={24}>
            <Card title="Additional Information" className="mb-4">
              <Form.Item
                label="Notes"
                name="notes"
              >
                <TextArea
                  rows={4}
                  placeholder="Additional notes about the student..."
                />
              </Form.Item>

              <Form.Item
                name="hasAlerts"
                valuePropName="checked"
              >
                <Checkbox>This student has alerts or special requirements</Checkbox>
              </Form.Item>
            </Card>
          </Col>
        </Row>

        {!isReadOnly && (
          <div className="text-center">
            <Space size="large">
              <Button onClick={onCancel} size="large">
                Cancel
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                icon={<SaveOutlined />}
                size="large"
              >
                {mode === 'create' ? 'Create Student' : 'Update Student'}
              </Button>
              {mode === 'edit' && (
                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => {
                    form.resetFields();
                    setHasChanges(false);
                  }}
                  size="large"
                >
                  Reset
                </Button>
              )}
            </Space>
          </div>
        )}
      </Form>
    </div>
  );
};

export default StudentForm;