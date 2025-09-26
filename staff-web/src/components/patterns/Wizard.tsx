/**
 * Wizard Pattern
 *
 * A multi-step wizard component for complex form workflows:
 * - Step navigation with validation
 * - Progress tracking
 * - Data persistence between steps
 * - Auto-save functionality
 * - Validation at each step
 * - Responsive design
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Steps,
  Button,
  Card,
  Form,
  Space,
  Divider,
  Progress,
  Alert,
  Spin,
  message,
} from 'antd';
import {
  CheckOutlined,
  ExclamationCircleOutlined,
  SaveOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';

const { Step } = Steps;

export interface WizardStep {
  key: string;
  title: string;
  description?: string;
  icon?: React.ReactNode;
  content: React.ReactNode;
  optional?: boolean;
  validate?: () => Promise<boolean> | boolean;
  onEnter?: () => void | Promise<void>;
  onLeave?: () => void | Promise<void>;
}

export interface WizardProps {
  // Steps
  steps: WizardStep[];
  current?: number;
  onStepChange?: (step: number) => void;

  // Form
  form?: any; // Ant Design form instance
  initialValues?: Record<string, any>;
  onValuesChange?: (changedValues: any, allValues: any) => void;

  // Navigation
  showStepNavigation?: boolean;
  allowStepJumping?: boolean;

  // Actions
  onFinish?: (values: any) => void | Promise<void>;
  onCancel?: () => void;
  onSaveDraft?: (values: any) => void | Promise<void>;

  // Auto-save
  autoSave?: boolean;
  autoSaveInterval?: number; // milliseconds

  // Loading
  loading?: boolean;
  submitting?: boolean;

  // Layout
  direction?: 'horizontal' | 'vertical';
  size?: 'default' | 'small';
  showProgress?: boolean;

  // Customization
  finishButtonText?: string;
  nextButtonText?: string;
  prevButtonText?: string;
  saveDraftButtonText?: string;
}

export const Wizard: React.FC<WizardProps> = ({
  steps,
  current = 0,
  onStepChange,
  form,
  initialValues = {},
  onValuesChange,
  showStepNavigation = true,
  allowStepJumping = false,
  onFinish,
  onCancel,
  onSaveDraft,
  autoSave = false,
  autoSaveInterval = 30000,
  loading = false,
  submitting = false,
  direction = 'horizontal',
  size = 'default',
  showProgress = true,
  finishButtonText = 'Finish',
  nextButtonText = 'Next',
  prevButtonText = 'Previous',
  saveDraftButtonText = 'Save Draft',
}) => {
  const [currentStep, setCurrentStep] = useState(current);
  const [stepStatuses, setStepStatuses] = useState<Record<number, 'wait' | 'process' | 'finish' | 'error'>>({});
  const [stepValidations, setStepValidations] = useState<Record<number, boolean>>({});
  const [autoSaveTimer, setAutoSaveTimer] = useState<NodeJS.Timeout | null>(null);

  // Initialize step statuses
  useEffect(() => {
    const statuses: Record<number, 'wait' | 'process' | 'finish' | 'error'> = {};
    steps.forEach((_, index) => {
      if (index < currentStep) {
        statuses[index] = 'finish';
      } else if (index === currentStep) {
        statuses[index] = 'process';
      } else {
        statuses[index] = 'wait';
      }
    });
    setStepStatuses(statuses);
  }, [currentStep, steps]);

  // Auto-save functionality
  useEffect(() => {
    if (autoSave && onSaveDraft && form) {
      const timer = setInterval(() => {
        const values = form.getFieldsValue();
        onSaveDraft(values);
      }, autoSaveInterval);

      setAutoSaveTimer(timer);

      return () => {
        if (timer) {
          clearInterval(timer);
        }
      };
    }
  }, [autoSave, onSaveDraft, form, autoSaveInterval]);

  // Cleanup auto-save timer
  useEffect(() => {
    return () => {
      if (autoSaveTimer) {
        clearInterval(autoSaveTimer);
      }
    };
  }, [autoSaveTimer]);

  // Handle step validation
  const validateStep = useCallback(async (stepIndex: number): Promise<boolean> => {
    const step = steps[stepIndex];
    if (!step.validate) return true;

    try {
      const isValid = await step.validate();
      setStepValidations(prev => ({ ...prev, [stepIndex]: isValid }));

      if (!isValid) {
        setStepStatuses(prev => ({ ...prev, [stepIndex]: 'error' }));
      } else {
        setStepStatuses(prev => ({ ...prev, [stepIndex]: 'finish' }));
      }

      return isValid;
    } catch (error) {
      console.error('Step validation error:', error);
      setStepValidations(prev => ({ ...prev, [stepIndex]: false }));
      setStepStatuses(prev => ({ ...prev, [stepIndex]: 'error' }));
      return false;
    }
  }, [steps]);

  // Handle step change
  const handleStepChange = useCallback(async (newStep: number) => {
    if (newStep === currentStep) return;

    // Validate current step before moving forward
    if (newStep > currentStep) {
      const isValid = await validateStep(currentStep);
      if (!isValid) {
        message.error('Please complete the current step before proceeding.');
        return;
      }
    }

    // Call onLeave for current step
    const currentStepConfig = steps[currentStep];
    if (currentStepConfig?.onLeave) {
      try {
        await currentStepConfig.onLeave();
      } catch (error) {
        console.error('Error leaving step:', error);
        return;
      }
    }

    // Call onEnter for new step
    const newStepConfig = steps[newStep];
    if (newStepConfig?.onEnter) {
      try {
        await newStepConfig.onEnter();
      } catch (error) {
        console.error('Error entering step:', error);
        return;
      }
    }

    setCurrentStep(newStep);
    onStepChange?.(newStep);
  }, [currentStep, steps, validateStep, onStepChange]);

  // Navigation handlers
  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      handleStepChange(currentStep + 1);
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      handleStepChange(currentStep - 1);
    }
  };

  const handleFinish = async () => {
    // Validate current step
    const isValid = await validateStep(currentStep);
    if (!isValid) {
      message.error('Please complete all required fields.');
      return;
    }

    // Get form values and submit
    if (form && onFinish) {
      try {
        const values = form.getFieldsValue();
        await onFinish(values);
      } catch (error) {
        console.error('Finish error:', error);
        message.error('An error occurred while submitting the form.');
      }
    }
  };

  const handleSaveDraft = async () => {
    if (form && onSaveDraft) {
      try {
        const values = form.getFieldsValue();
        await onSaveDraft(values);
        message.success('Draft saved successfully.');
      } catch (error) {
        console.error('Save draft error:', error);
        message.error('Failed to save draft.');
      }
    }
  };

  // Calculate progress
  const progress = Math.round(((currentStep + 1) / steps.length) * 100);

  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === steps.length - 1;
  const currentStepConfig = steps[currentStep];

  return (
    <div className="wizard-container">
      <Spin spinning={loading}>
        <Card>
          {/* Progress bar */}
          {showProgress && (
            <div className="mb-6">
              <Progress
                percent={progress}
                showInfo={false}
                strokeColor="#1890ff"
                className="mb-2"
              />
              <div className="text-center text-sm text-gray-500">
                Step {currentStep + 1} of {steps.length}
              </div>
            </div>
          )}

          {/* Steps navigation */}
          {showStepNavigation && (
            <div className="mb-6">
              <Steps
                current={currentStep}
                direction={direction}
                size={size}
                onChange={allowStepJumping ? handleStepChange : undefined}
              >
                {steps.map((step, index) => (
                  <Step
                    key={step.key}
                    title={step.title}
                    description={step.description}
                    icon={step.icon}
                    status={stepStatuses[index]}
                    disabled={!allowStepJumping}
                  />
                ))}
              </Steps>
            </div>
          )}

          <Divider />

          {/* Step content */}
          <div className="step-content mb-6">
            <div className="mb-4">
              <h3 className="text-lg font-semibold">
                {currentStepConfig?.title}
              </h3>
              {currentStepConfig?.description && (
                <p className="text-gray-600 mt-1">
                  {currentStepConfig.description}
                </p>
              )}
              {currentStepConfig?.optional && (
                <Alert
                  message="This step is optional"
                  type="info"
                  showIcon
                  className="mt-2"
                />
              )}
            </div>

            <Form
              form={form}
              layout="vertical"
              initialValues={initialValues}
              onValuesChange={onValuesChange}
            >
              {currentStepConfig?.content}
            </Form>
          </div>

          {/* Navigation buttons */}
          <div className="flex justify-between items-center">
            <div>
              {!isFirstStep && (
                <Button
                  onClick={handlePrev}
                  icon={<ArrowLeftOutlined />}
                  disabled={loading || submitting}
                >
                  {prevButtonText}
                </Button>
              )}
            </div>

            <Space>
              {onSaveDraft && (
                <Button
                  onClick={handleSaveDraft}
                  icon={<SaveOutlined />}
                  disabled={loading || submitting}
                >
                  {saveDraftButtonText}
                </Button>
              )}

              {onCancel && (
                <Button
                  onClick={onCancel}
                  disabled={loading || submitting}
                >
                  Cancel
                </Button>
              )}

              {isLastStep ? (
                <Button
                  type="primary"
                  onClick={handleFinish}
                  loading={submitting}
                  disabled={loading}
                  icon={<CheckOutlined />}
                >
                  {finishButtonText}
                </Button>
              ) : (
                <Button
                  type="primary"
                  onClick={handleNext}
                  disabled={loading || submitting}
                  icon={<ArrowRightOutlined />}
                >
                  {nextButtonText}
                </Button>
              )}
            </Space>
          </div>

          {/* Auto-save indicator */}
          {autoSave && (
            <div className="mt-4 text-center">
              <span className="text-xs text-gray-500">
                Auto-saving every {autoSaveInterval / 1000} seconds
              </span>
            </div>
          )}
        </Card>
      </Spin>
    </div>
  );
};

export default Wizard;