/**
 * Multi-Step Workflow Wizard Pattern - Core Exports
 * Simplified implementation focusing on essential wizard functionality
 */

export interface WizardStep {
  id: string;
  title: string;
  description?: string;
  component: React.ComponentType<any>;
  validation?: (data: any) => { valid: boolean; errors?: Record<string, string> };
  canSkip?: boolean;
  isOptional?: boolean;
}

export interface WizardProps {
  steps: WizardStep[];
  currentStep?: number;
  onStepChange?: (step: number) => void;
  onComplete?: (data: any) => void;
  onCancel?: () => void;
  data?: Record<string, any>;
  className?: string;
}

// Simplified Wizard component
import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, Check } from 'lucide-react';

export const Wizard: React.FC<WizardProps> = ({
  steps,
  currentStep = 0,
  onStepChange,
  onComplete,
  onCancel,
  data = {},
  className = ''
}) => {
  const [wizardData, setWizardData] = useState(data);
  const [currentStepIndex, setCurrentStepIndex] = useState(currentStep);

  const currentStepData = steps[currentStepIndex];
  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === steps.length - 1;

  const handleNext = () => {
    if (currentStepData.validation) {
      const validation = currentStepData.validation(wizardData);
      if (!validation.valid) {
        // Handle validation errors
        return;
      }
    }

    if (isLastStep) {
      onComplete?.(wizardData);
    } else {
      const nextStep = currentStepIndex + 1;
      setCurrentStepIndex(nextStep);
      onStepChange?.(nextStep);
    }
  };

  const handlePrevious = () => {
    if (!isFirstStep) {
      const prevStep = currentStepIndex - 1;
      setCurrentStepIndex(prevStep);
      onStepChange?.(prevStep);
    }
  };

  const handleStepClick = (stepIndex: number) => {
    if (stepIndex <= currentStepIndex) {
      setCurrentStepIndex(stepIndex);
      onStepChange?.(stepIndex);
    }
  };

  return (
    <div className={`wizard-container bg-white rounded-lg shadow ${className}`}>
      {/* Step indicator */}
      <div className="border-b border-gray-200 px-6 py-4">
        <nav className="flex space-x-4">
          {steps.map((step, index) => (
            <button
              key={step.id}
              onClick={() => handleStepClick(index)}
              disabled={index > currentStepIndex}
              className={`
                flex items-center space-x-2 px-4 py-2 rounded-md text-sm font-medium
                ${index < currentStepIndex ? 'bg-green-100 text-green-800' :
                  index === currentStepIndex ? 'bg-blue-100 text-blue-800' :
                  'bg-gray-100 text-gray-400'}
                ${index <= currentStepIndex ? 'cursor-pointer' : 'cursor-not-allowed'}
              `}
            >
              {index < currentStepIndex ? (
                <Check className="w-4 h-4" />
              ) : (
                <span className="w-4 h-4 rounded-full bg-current opacity-20" />
              )}
              <span>{step.title}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Step content */}
      <div className="p-6">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900">{currentStepData.title}</h2>
          {currentStepData.description && (
            <p className="text-gray-600 mt-2">{currentStepData.description}</p>
          )}
        </div>

        <div className="wizard-step-content">
          <currentStepData.component
            data={wizardData}
            onChange={setWizardData}
          />
        </div>
      </div>

      {/* Navigation */}
      <div className="border-t border-gray-200 px-6 py-4 flex justify-between">
        <div>
          {!isFirstStep && (
            <button
              onClick={handlePrevious}
              className="flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Previous</span>
            </button>
          )}
        </div>

        <div className="flex space-x-3">
          {onCancel && (
            <button
              onClick={onCancel}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              Cancel
            </button>
          )}

          <button
            onClick={handleNext}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            <span>{isLastStep ? 'Complete' : 'Next'}</span>
            {!isLastStep && <ChevronRight className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Wizard;