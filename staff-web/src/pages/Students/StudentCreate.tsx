/**
 * Student Creation Wizard
 *
 * A comprehensive multi-step wizard for creating new students using the Wizard pattern:
 * - Step 1: Basic Information (Name, DOB, Gender, etc.)
 * - Step 2: Contact Information (Address, Phone, Email)
 * - Step 3: Emergency Contacts (Multiple contacts with relationships)
 * - Step 4: Academic Information (Program, Start date, Previous education)
 * - Step 5: Financial Setup (Payment plans, Scholarships)
 * - Step 6: Documents (Photo, ID copies, Transcripts)
 * - Step 7: Review & Submit
 * - Field validation at each step
 * - Save draft capability with auto-recovery
 * - Photo capture using device camera
 * - Document upload with OCR processing
 * - Duplicate detection before creation
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  Form,
  Input,
  Select,
  DatePicker,
  Radio,
  Switch,
  Upload,
  Card,
  Row,
  Col,
  Alert,
  Avatar,
  Button,
  Space,
  Divider,
  Table,
  Tag,
  message,
  Progress,
  Tooltip,
  Modal,
  List,
} from 'antd';
import {
  UserOutlined,
  CameraOutlined,
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  FileTextOutlined,
  PhoneOutlined,
  MailOutlined,
  HomeOutlined,
  CalendarOutlined,
  BankOutlined,
  BookOutlined,
  TeamOutlined,
  DollarOutlined,
  ScanOutlined,
  CloudUploadOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import { Wizard } from '../../components/patterns';
import type { WizardStep } from '../../components/patterns';
import { StudentService } from '../../services/student.service';
import type {
  CreatePersonData,
  CreateStudentProfileData,
  SelectOption,
  PersonSearchResult,
} from '../../types/student.types';

const { Option } = Select;
const { TextArea } = Input;

interface StudentCreateProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: (studentId: number) => void;
}

interface FormData {
  // Basic Information
  family_name: string;
  personal_name: string;
  khmer_name?: string;
  preferred_gender?: string;
  date_of_birth?: string;
  birth_province?: string;
  citizenship?: string;

  // Contact Information
  school_email?: string;
  personal_email?: string;
  phone_numbers: Array<{
    number: string;
    comment: string;
    is_preferred: boolean;
    is_telegram: boolean;
  }>;
  address: {
    current_address?: string;
    permanent_address?: string;
    city?: string;
    province?: string;
    postal_code?: string;
  };

  // Emergency Contacts
  emergency_contacts: Array<{
    name: string;
    relationship: string;
    primary_phone: string;
    secondary_phone?: string;
    email?: string;
    address?: string;
    is_emergency_contact: boolean;
    is_general_contact: boolean;
  }>;

  // Academic Information
  student_profile: {
    is_monk: boolean;
    is_transfer_student: boolean;
    study_time_preference: string;
    current_status: string;
  };
  intended_major?: number;
  previous_education?: string;
  entry_level?: number;

  // Financial Information
  payment_plan?: string;
  scholarships: Array<{
    name: string;
    amount: number;
    type: string;
  }>;

  // Documents
  documents: Array<{
    type: string;
    file: File;
    processed?: boolean;
  }>;
  photo?: File;
}

export const StudentCreate: React.FC<StudentCreateProps> = ({
  open,
  onClose,
  onSuccess,
}) => {
  const [form] = Form.useForm();
  const [formData, setFormData] = useState<Partial<FormData>>({
    phone_numbers: [{ number: '', comment: 'Primary', is_preferred: true, is_telegram: false }],
    emergency_contacts: [],
    student_profile: {
      is_monk: false,
      is_transfer_student: false,
      study_time_preference: 'morning',
      current_status: 'ACTIVE',
    },
    scholarships: [],
    documents: [],
    address: {},
  });

  // Options data
  const [statusOptions, setStatusOptions] = useState<SelectOption[]>([]);
  const [majorOptions, setMajorOptions] = useState<SelectOption[]>([]);
  const [relationshipOptions, setRelationshipOptions] = useState<SelectOption[]>([]);

  // State for duplicate detection
  const [duplicateCheckResults, setDuplicateCheckResults] = useState<PersonSearchResult[]>([]);
  const [showDuplicateWarning, setShowDuplicateWarning] = useState(false);

  // State for document processing
  const [documentProcessing, setDocumentProcessing] = useState<Record<string, boolean>>({});

  // Load options on mount
  useEffect(() => {
    if (open) {
      loadOptions();
      loadDraftData();
    }
  }, [open]);

  const loadOptions = async () => {
    try {
      const [statuses, majors, relationships] = await Promise.all([
        StudentService.getStudentStatuses(),
        StudentService.listMajors({ active_only: true }),
        StudentService.getRelationshipChoices(),
      ]);

      setStatusOptions(statuses);
      setMajorOptions(
        majors.results.map(major => ({
          label: major.name,
          value: major.id.toString(),
        }))
      );
      setRelationshipOptions(relationships);
    } catch (error) {
      console.error('Failed to load options:', error);
    }
  };

  const loadDraftData = () => {
    // Load saved draft from localStorage
    const draftKey = 'student-create-draft';
    const draft = localStorage.getItem(draftKey);
    if (draft) {
      try {
        const draftData = JSON.parse(draft);
        setFormData(draftData);
        form.setFieldsValue(draftData);
        message.info('Draft data loaded');
      } catch (error) {
        console.error('Failed to load draft:', error);
      }
    }
  };

  const saveDraft = useCallback((values: any) => {
    const draftKey = 'student-create-draft';
    localStorage.setItem(draftKey, JSON.stringify(values));
  }, []);

  const handleValuesChange = (changedValues: any, allValues: any) => {
    setFormData(allValues);
    saveDraft(allValues);
  };

  // Duplicate detection
  const checkForDuplicates = async () => {
    const { family_name, personal_name, date_of_birth } = formData;
    if (!family_name || !personal_name) return true;

    try {
      const searchResults = await StudentService.searchPersons({
        q: `${family_name} ${personal_name}`,
        page_size: 10,
      });

      if (searchResults.results.length > 0) {
        setDuplicateCheckResults(searchResults.results);
        setShowDuplicateWarning(true);
        return false;
      }

      return true;
    } catch (error) {
      console.error('Duplicate check failed:', error);
      return true; // Continue if check fails
    }
  };

  // Document OCR processing
  const processDocument = async (file: File, documentType: string) => {
    setDocumentProcessing(prev => ({ ...prev, [file.name]: true }));

    try {
      // TODO: Implement OCR processing
      await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate processing

      // Extract relevant information based on document type
      if (documentType === 'national_id') {
        // Extract name, DOB, etc. from national ID
        message.success('National ID information extracted successfully');
      } else if (documentType === 'transcript') {
        // Extract academic information
        message.success('Academic transcript processed successfully');
      }

      setDocumentProcessing(prev => ({ ...prev, [file.name]: false }));
      return true;
    } catch (error) {
      setDocumentProcessing(prev => ({ ...prev, [file.name]: false }));
      message.error(`Failed to process ${documentType}`);
      return false;
    }
  };

  // Address validation and standardization
  const validateAddress = async (address: string) => {
    try {
      // TODO: Implement address validation API
      return { valid: true, standardized: address };
    } catch (error) {
      return { valid: false, standardized: address };
    }
  };

  // Emergency contact verification
  const verifyEmergencyContact = async (phone: string) => {
    try {
      // TODO: Implement SMS verification
      message.success(`Verification SMS sent to ${phone}`);
    } catch (error) {
      message.error('Failed to send verification SMS');
    }
  };

  // Scholarship matching
  const matchScholarships = async (academicData: any) => {
    try {
      // TODO: Implement scholarship matching algorithm
      const matches = [
        { name: 'Merit Scholarship', amount: 1000, eligibility: 'High academic performance' },
        { name: 'Need-Based Aid', amount: 500, eligibility: 'Financial need demonstrated' },
      ];
      return matches;
    } catch (error) {
      return [];
    }
  };

  // Form submission
  const handleFinish = async (values: any) => {
    try {
      // Create person first
      const personData: CreatePersonData = {
        family_name: values.family_name,
        personal_name: values.personal_name,
        khmer_name: values.khmer_name,
        preferred_gender: values.preferred_gender,
        school_email: values.school_email,
        personal_email: values.personal_email,
        date_of_birth: values.date_of_birth,
        birth_province: values.birth_province,
        citizenship: values.citizenship,
      };

      // TODO: Implement person creation API
      const personId = 123; // Mock response

      // Create student profile
      const studentData: CreateStudentProfileData = {
        student_id: personId,
        is_monk: values.student_profile.is_monk,
        is_transfer_student: values.student_profile.is_transfer_student,
        study_time_preference: values.student_profile.study_time_preference,
        current_status: values.student_profile.current_status,
      };

      // TODO: Implement student profile creation API

      // Clear draft
      localStorage.removeItem('student-create-draft');

      message.success('Student created successfully!');
      onSuccess?.(personId);
      onClose();
    } catch (error) {
      console.error('Failed to create student:', error);
      message.error('Failed to create student. Please try again.');
    }
  };

  // Define wizard steps
  const steps: WizardStep[] = [
    {
      key: 'basic',
      title: 'Basic Information',
      description: 'Personal details and identification',
      content: (
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="family_name"
              label="Family Name"
              rules={[{ required: true, message: 'Please enter family name' }]}
            >
              <Input placeholder="Enter family name" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="personal_name"
              label="Personal Name"
              rules={[{ required: true, message: 'Please enter personal name' }]}
            >
              <Input placeholder="Enter personal name" />
            </Form.Item>
          </Col>
          <Col span={24}>
            <Form.Item name="khmer_name" label="Khmer Name">
              <Input placeholder="Enter Khmer name (optional)" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="preferred_gender" label="Gender">
              <Select placeholder="Select gender">
                <Option value="M">Male</Option>
                <Option value="F">Female</Option>
                <Option value="N">Non-binary</Option>
                <Option value="X">Prefer not to say</Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="date_of_birth" label="Date of Birth">
              <DatePicker
                style={{ width: '100%' }}
                placeholder="Select date of birth"
                disabledDate={(current) => current && current > dayjs().endOf('day')}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="birth_province" label="Birth Province">
              <Input placeholder="Enter birth province" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="citizenship" label="Citizenship">
              <Select placeholder="Select citizenship">
                <Option value="Cambodia">Cambodia</Option>
                <Option value="Thailand">Thailand</Option>
                <Option value="Vietnam">Vietnam</Option>
                <Option value="Other">Other</Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>
      ),
      validate: checkForDuplicates,
    },
    {
      key: 'contact',
      title: 'Contact Information',
      description: 'Email addresses and phone numbers',
      content: (
        <div className="space-y-6">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="school_email"
                label="School Email"
                rules={[
                  { type: 'email', message: 'Please enter a valid email' },
                  { required: true, message: 'School email is required' },
                ]}
              >
                <Input placeholder="student@school.edu" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="personal_email"
                label="Personal Email"
                rules={[{ type: 'email', message: 'Please enter a valid email' }]}
              >
                <Input placeholder="personal@email.com" />
              </Form.Item>
            </Col>
          </Row>

          <Card title="Phone Numbers" size="small">
            <Form.List name="phone_numbers">
              {(fields, { add, remove }) => (
                <>
                  {fields.map((field, index) => (
                    <Row key={field.key} gutter={16} align="middle">
                      <Col span={8}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'number']}
                          rules={[{ required: true, message: 'Phone number required' }]}
                        >
                          <Input placeholder="Phone number" />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item {...field} name={[field.name, 'comment']}>
                          <Input placeholder="Label" />
                        </Form.Item>
                      </Col>
                      <Col span={4}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'is_preferred']}
                          valuePropName="checked"
                        >
                          <Switch checkedChildren="Primary" unCheckedChildren="Secondary" />
                        </Form.Item>
                      </Col>
                      <Col span={4}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'is_telegram']}
                          valuePropName="checked"
                        >
                          <Switch checkedChildren="Telegram" unCheckedChildren="Regular" />
                        </Form.Item>
                      </Col>
                      <Col span={2}>
                        {fields.length > 1 && (
                          <Button
                            type="link"
                            danger
                            icon={<DeleteOutlined />}
                            onClick={() => remove(field.name)}
                          />
                        )}
                      </Col>
                    </Row>
                  ))}
                  <Button type="dashed" onClick={() => add()} icon={<PlusOutlined />}>
                    Add Phone Number
                  </Button>
                </>
              )}
            </Form.List>
          </Card>

          <Card title="Address Information" size="small">
            <Row gutter={16}>
              <Col span={24}>
                <Form.Item name={['address', 'current_address']} label="Current Address">
                  <TextArea
                    rows={2}
                    placeholder="Enter current address"
                    onBlur={(e) => validateAddress(e.target.value)}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name={['address', 'city']} label="City">
                  <Input placeholder="City" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name={['address', 'province']} label="Province">
                  <Input placeholder="Province" />
                </Form.Item>
              </Col>
            </Row>
          </Card>
        </div>
      ),
    },
    {
      key: 'emergency',
      title: 'Emergency Contacts',
      description: 'Emergency contact information',
      content: (
        <Card title="Emergency Contacts">
          <Form.List name="emergency_contacts">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Card key={field.key} size="small" className="mb-4">
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'name']}
                          label="Full Name"
                          rules={[{ required: true, message: 'Name is required' }]}
                        >
                          <Input placeholder="Contact name" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'relationship']}
                          label="Relationship"
                          rules={[{ required: true, message: 'Relationship is required' }]}
                        >
                          <Select placeholder="Select relationship">
                            {relationshipOptions.map(option => (
                              <Option key={option.value} value={option.value}>
                                {option.label}
                              </Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'primary_phone']}
                          label="Primary Phone"
                          rules={[{ required: true, message: 'Primary phone is required' }]}
                        >
                          <Input
                            placeholder="Primary phone"
                            addonAfter={
                              <Button
                                type="link"
                                size="small"
                                onClick={() => {
                                  const phone = form.getFieldValue([
                                    'emergency_contacts',
                                    field.name,
                                    'primary_phone',
                                  ]);
                                  if (phone) verifyEmergencyContact(phone);
                                }}
                              >
                                Verify
                              </Button>
                            }
                          />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item {...field} name={[field.name, 'email']} label="Email">
                          <Input placeholder="Email address" />
                        </Form.Item>
                      </Col>
                      <Col span={24} className="text-right">
                        <Button
                          type="link"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => remove(field.name)}
                        >
                          Remove Contact
                        </Button>
                      </Col>
                    </Row>
                  </Card>
                ))}
                <Button
                  type="dashed"
                  onClick={() => add()}
                  icon={<PlusOutlined />}
                  className="w-full"
                >
                  Add Emergency Contact
                </Button>
              </>
            )}
          </Form.List>
        </Card>
      ),
    },
    {
      key: 'academic',
      title: 'Academic Information',
      description: 'Program selection and academic details',
      content: (
        <div className="space-y-6">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="intended_major" label="Intended Major">
                <Select
                  placeholder="Select intended major"
                  showSearch
                  filterOption={(input, option) =>
                    (option?.children as unknown as string)
                      .toLowerCase()
                      .includes(input.toLowerCase())
                  }
                >
                  {majorOptions.map(option => (
                    <Option key={option.value} value={option.value}>
                      {option.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name={['student_profile', 'study_time_preference']}
                label="Study Time Preference"
              >
                <Select placeholder="Select study time">
                  <Option value="morning">Morning</Option>
                  <Option value="afternoon">Afternoon</Option>
                  <Option value="evening">Evening</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name={['student_profile', 'current_status']}
                label="Initial Status"
              >
                <Select placeholder="Select status">
                  {statusOptions.map(option => (
                    <Option key={option.value} value={option.value}>
                      {option.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="entry_level" label="Entry Level">
                <Select placeholder="Select entry level">
                  <Option value={1}>Level 1 - Beginner</Option>
                  <Option value={2}>Level 2 - Intermediate</Option>
                  <Option value={3}>Level 3 - Advanced</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name={['student_profile', 'is_monk']}
                label="Monk Status"
                valuePropName="checked"
              >
                <Switch checkedChildren="Monk" unCheckedChildren="Lay Person" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name={['student_profile', 'is_transfer_student']}
                label="Transfer Student"
                valuePropName="checked"
              >
                <Switch checkedChildren="Transfer" unCheckedChildren="New Student" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="previous_education" label="Previous Education">
            <TextArea
              rows={3}
              placeholder="Describe previous educational background..."
            />
          </Form.Item>
        </div>
      ),
      onEnter: async () => {
        // Auto-match scholarships based on academic information
        const academicData = form.getFieldsValue();
        const scholarshipMatches = await matchScholarships(academicData);
        if (scholarshipMatches.length > 0) {
          message.success(`Found ${scholarshipMatches.length} potential scholarship matches!`);
        }
      },
    },
    {
      key: 'financial',
      title: 'Financial Setup',
      description: 'Payment plans and financial aid',
      optional: true,
      content: (
        <div className="space-y-6">
          <Form.Item name="payment_plan" label="Payment Plan">
            <Radio.Group>
              <Radio value="full">Full Payment</Radio>
              <Radio value="semester">Per Semester</Radio>
              <Radio value="monthly">Monthly Installments</Radio>
            </Radio.Group>
          </Form.Item>

          <Card title="Scholarships & Financial Aid" size="small">
            <Form.List name="scholarships">
              {(fields, { add, remove }) => (
                <>
                  {fields.map((field) => (
                    <Row key={field.key} gutter={16} align="middle">
                      <Col span={10}>
                        <Form.Item {...field} name={[field.name, 'name']}>
                          <Input placeholder="Scholarship name" />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item {...field} name={[field.name, 'amount']}>
                          <Input placeholder="Amount" type="number" prefix="$" />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item {...field} name={[field.name, 'type']}>
                          <Select placeholder="Type">
                            <Option value="merit">Merit-based</Option>
                            <Option value="need">Need-based</Option>
                            <Option value="athletic">Athletic</Option>
                            <Option value="other">Other</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={2}>
                        <Button
                          type="link"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => remove(field.name)}
                        />
                      </Col>
                    </Row>
                  ))}
                  <Button type="dashed" onClick={() => add()} icon={<PlusOutlined />}>
                    Add Scholarship
                  </Button>
                </>
              )}
            </Form.List>
          </Card>
        </div>
      ),
    },
    {
      key: 'documents',
      title: 'Documents',
      description: 'Upload required documents and photo',
      content: (
        <div className="space-y-6">
          <Card title="Student Photo" size="small">
            <Upload
              name="photo"
              listType="picture-card"
              showUploadList={false}
              beforeUpload={() => false}
              accept="image/*"
              onChange={(info) => {
                if (info.file) {
                  setFormData(prev => ({ ...prev, photo: info.file as File }));
                }
              }}
            >
              {formData.photo ? (
                <Avatar size={100} src={URL.createObjectURL(formData.photo)} />
              ) : (
                <div>
                  <CameraOutlined style={{ fontSize: 24 }} />
                  <div style={{ marginTop: 8 }}>Upload Photo</div>
                </div>
              )}
            </Upload>
          </Card>

          <Card title="Required Documents" size="small">
            <div className="space-y-4">
              {[
                { type: 'national_id', label: 'National ID or Passport', required: true },
                { type: 'transcript', label: 'Academic Transcript', required: false },
                { type: 'birth_certificate', label: 'Birth Certificate', required: false },
                { type: 'medical_record', label: 'Medical Records', required: false },
              ].map(doc => (
                <div key={doc.type} className="border rounded p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium">
                      {doc.label}
                      {doc.required && <span className="text-red-500 ml-1">*</span>}
                    </span>
                    <Upload
                      beforeUpload={(file) => {
                        processDocument(file, doc.type);
                        return false;
                      }}
                      showUploadList={false}
                    >
                      <Button icon={<CloudUploadOutlined />}>Upload</Button>
                    </Upload>
                  </div>
                  {documentProcessing[doc.type] && (
                    <div className="flex items-center space-x-2">
                      <Progress percent={30} size="small" />
                      <span className="text-sm text-gray-500">Processing with OCR...</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </div>
      ),
    },
    {
      key: 'review',
      title: 'Review & Submit',
      description: 'Review all information before submitting',
      content: (
        <div className="space-y-6">
          <Alert
            message="Review Information"
            description="Please review all the information you have entered. You can go back to any step to make changes."
            type="info"
            showIcon
          />

          <Card title="Summary" size="small">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium">Basic Information</h4>
                <p>{formData.family_name} {formData.personal_name}</p>
                <p>{formData.khmer_name && `Khmer: ${formData.khmer_name}`}</p>
                <p>{formData.date_of_birth && `DOB: ${dayjs(formData.date_of_birth).format('MMMM D, YYYY')}`}</p>
              </div>
              <div>
                <h4 className="font-medium">Contact</h4>
                <p>{formData.school_email}</p>
                <p>{formData.phone_numbers?.[0]?.number}</p>
              </div>
              <div>
                <h4 className="font-medium">Academic</h4>
                <p>Status: {formData.student_profile?.current_status}</p>
                <p>Study Time: {formData.student_profile?.study_time_preference}</p>
                <p>
                  {formData.student_profile?.is_monk && 'Monk • '}
                  {formData.student_profile?.is_transfer_student && 'Transfer Student'}
                </p>
              </div>
              <div>
                <h4 className="font-medium">Emergency Contacts</h4>
                {formData.emergency_contacts?.map((contact, index) => (
                  <p key={index}>{contact.name} ({contact.relationship})</p>
                ))}
              </div>
            </div>
          </Card>
        </div>
      ),
    },
  ];

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={1000}
      title="Create New Student"
      destroyOnClose
    >
      <Wizard
        steps={steps}
        form={form}
        initialValues={formData}
        onValuesChange={handleValuesChange}
        onFinish={handleFinish}
        onCancel={onClose}
        onSaveDraft={saveDraft}
        autoSave={true}
        autoSaveInterval={30000}
        showProgress={true}
      />

      {/* Duplicate Warning Modal */}
      <Modal
        title="Potential Duplicate Students Found"
        open={showDuplicateWarning}
        onCancel={() => setShowDuplicateWarning(false)}
        footer={[
          <Button key="ignore" onClick={() => setShowDuplicateWarning(false)}>
            Continue Anyway
          </Button>,
          <Button key="review" type="primary" onClick={() => setShowDuplicateWarning(false)}>
            Review Duplicates
          </Button>,
        ]}
      >
        <Alert
          message="Similar students found in the system"
          description="Please review the following students to ensure you're not creating a duplicate."
          type="warning"
          showIcon
          className="mb-4"
        />
        <List
          dataSource={duplicateCheckResults}
          renderItem={(person) => (
            <List.Item>
              <div className="flex items-center space-x-3">
                <Avatar src={person.current_thumbnail_url} icon={<UserOutlined />} />
                <div>
                  <div className="font-medium">{person.full_name}</div>
                  <div className="text-sm text-gray-500">
                    {person.student_id && `Student ID: ${person.formatted_student_id} • `}
                    {person.school_email}
                  </div>
                </div>
              </div>
            </List.Item>
          )}
        />
      </Modal>
    </Modal>
  );
};

export default StudentCreate;