/**
 * Transfer Controls Component
 * Central controls for transferring items between lists
 */

import React, { useState } from 'react';
import {
  ChevronRight,
  ChevronLeft,
  ChevronsRight,
  ChevronsLeft,
  Copy,
  Undo,
  Redo,
  Save,
  History,
  AlertTriangle,
  CheckCircle,
  Info,
  Play
} from 'lucide-react';
import {
  TransferDraft,
  TransferValidationRule
} from '../types';

interface TransferControlsProps {
  // Transfer operations
  canTransferToRight: boolean;
  canTransferToLeft: boolean;
  leftSelectedCount: number;
  rightSelectedCount: number;
  leftTotalCount: number;
  rightTotalCount: number;

  onTransferToRight: () => void;
  onTransferToLeft: () => void;
  onTransferAllToRight: () => void;
  onTransferAllToLeft: () => void;

  // Copy mode
  allowCopy?: boolean;
  copyMode?: boolean;
  onToggleCopyMode?: () => void;

  // History
  undoable?: boolean;
  canUndo?: boolean;
  canRedo?: boolean;
  onUndo?: () => void;
  onRedo?: () => void;

  // Validation
  validationResults?: Array<{
    ruleId: string;
    valid: boolean;
    message?: string;
    severity?: 'error' | 'warning' | 'info';
  }>;
  isValid?: boolean;

  // Draft management
  draftable?: boolean;
  isDirty?: boolean;
  onSaveDraft?: () => void;
  onLoadDraft?: () => void;
  savedDrafts?: TransferDraft[];

  // Progress
  showProgress?: boolean;
  progress?: number;
  progressTarget?: number;

  // Auto-transfer
  autoTransfer?: boolean;
  onToggleAutoTransfer?: () => void;

  // Styling
  orientation?: 'vertical' | 'horizontal';
  compact?: boolean;
  className?: string;
}

export function TransferControls({
  canTransferToRight,
  canTransferToLeft,
  leftSelectedCount,
  rightSelectedCount,
  leftTotalCount,
  rightTotalCount,
  onTransferToRight,
  onTransferToLeft,
  onTransferAllToRight,
  onTransferAllToLeft,
  allowCopy = false,
  copyMode = false,
  onToggleCopyMode,
  undoable = false,
  canUndo = false,
  canRedo = false,
  onUndo,
  onRedo,
  validationResults = [],
  isValid = true,
  draftable = false,
  isDirty = false,
  onSaveDraft,
  onLoadDraft,
  savedDrafts = [],
  showProgress = false,
  progress = 0,
  progressTarget,
  autoTransfer = false,
  onToggleAutoTransfer,
  orientation = 'vertical',
  compact = false,
  className = ''
}: TransferControlsProps) {
  const [showValidation, setShowValidation] = useState(false);
  const [showDrafts, setShowDrafts] = useState(false);

  const hasErrors = validationResults.some(result => !result.valid && result.severity === 'error');
  const hasWarnings = validationResults.some(result => !result.valid && result.severity === 'warning');

  const progressPercentage = progressTarget ? (progress / progressTarget) * 100 : 0;

  const buttonBaseClass = `
    inline-flex items-center justify-center p-2 rounded-md border transition-all duration-150
    ${compact ? 'text-sm' : ''}
    disabled:opacity-50 disabled:cursor-not-allowed
  `;

  const primaryButtonClass = `
    ${buttonBaseClass}
    bg-blue-600 border-blue-600 text-white
    hover:bg-blue-700 hover:border-blue-700
    focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
  `;

  const secondaryButtonClass = `
    ${buttonBaseClass}
    bg-white border-gray-300 text-gray-700
    hover:bg-gray-50 hover:border-gray-400
    focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
  `;

  const dangerButtonClass = `
    ${buttonBaseClass}
    bg-red-600 border-red-600 text-white
    hover:bg-red-700 hover:border-red-700
    focus:ring-2 focus:ring-red-500 focus:ring-offset-2
  `;

  const warningButtonClass = `
    ${buttonBaseClass}
    bg-yellow-600 border-yellow-600 text-white
    hover:bg-yellow-700 hover:border-yellow-700
    focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2
  `;

  const renderButton = (
    icon: React.ReactNode,
    onClick: () => void,
    disabled: boolean,
    tooltip: string,
    variant: 'primary' | 'secondary' | 'danger' | 'warning' = 'secondary',
    badge?: string | number
  ) => {
    const variantClasses = {
      primary: primaryButtonClass,
      secondary: secondaryButtonClass,
      danger: dangerButtonClass,
      warning: warningButtonClass
    };

    return (
      <div className="relative">
        <button
          onClick={onClick}
          disabled={disabled}
          className={variantClasses[variant]}
          title={tooltip}
        >
          {icon}
        </button>
        {badge && (
          <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
            {badge}
          </span>
        )}
      </div>
    );
  };

  const transferButtons = (
    <>
      {/* Transfer selected to right */}
      {renderButton(
        <ChevronRight className="w-4 h-4" />,
        onTransferToRight,
        !canTransferToRight,
        `Transfer ${leftSelectedCount} selected items to right`,
        'primary',
        leftSelectedCount > 0 ? leftSelectedCount : undefined
      )}

      {/* Transfer all to right */}
      {renderButton(
        <ChevronsRight className="w-4 h-4" />,
        onTransferAllToRight,
        leftTotalCount === 0,
        'Transfer all items to right'
      )}

      {/* Transfer all to left */}
      {renderButton(
        <ChevronsLeft className="w-4 h-4" />,
        onTransferAllToLeft,
        rightTotalCount === 0,
        'Transfer all items to left'
      )}

      {/* Transfer selected to left */}
      {renderButton(
        <ChevronLeft className="w-4 h-4" />,
        onTransferToLeft,
        !canTransferToLeft,
        `Transfer ${rightSelectedCount} selected items to left`,
        'primary',
        rightSelectedCount > 0 ? rightSelectedCount : undefined
      )}
    </>
  );

  const utilityButtons = (
    <>
      {/* Copy mode toggle */}
      {allowCopy && onToggleCopyMode && renderButton(
        <Copy className="w-4 h-4" />,
        onToggleCopyMode,
        false,
        copyMode ? 'Switch to move mode' : 'Switch to copy mode',
        copyMode ? 'warning' : 'secondary'
      )}

      {/* Undo */}
      {undoable && onUndo && renderButton(
        <Undo className="w-4 h-4" />,
        onUndo,
        !canUndo,
        'Undo last operation'
      )}

      {/* Redo */}
      {undoable && onRedo && renderButton(
        <Redo className="w-4 h-4" />,
        onRedo,
        !canRedo,
        'Redo last operation'
      )}

      {/* Auto-transfer toggle */}
      {onToggleAutoTransfer && renderButton(
        <Play className="w-4 h-4" />,
        onToggleAutoTransfer,
        false,
        autoTransfer ? 'Disable auto-transfer' : 'Enable auto-transfer',
        autoTransfer ? 'warning' : 'secondary'
      )}
    </>
  );

  const statusButtons = (
    <>
      {/* Validation status */}
      {validationResults.length > 0 && (
        <div className="relative">
          <button
            onClick={() => setShowValidation(!showValidation)}
            className={`
              ${buttonBaseClass}
              ${hasErrors ? 'bg-red-100 border-red-300 text-red-700' :
                hasWarnings ? 'bg-yellow-100 border-yellow-300 text-yellow-700' :
                'bg-green-100 border-green-300 text-green-700'}
            `}
            title="Validation status"
          >
            {hasErrors ? (
              <AlertTriangle className="w-4 h-4" />
            ) : hasWarnings ? (
              <Info className="w-4 h-4" />
            ) : (
              <CheckCircle className="w-4 h-4" />
            )}
          </button>

          {showValidation && (
            <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-3 z-50 min-w-64">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Validation Results</h4>
              <div className="space-y-2">
                {validationResults.map(result => (
                  <div
                    key={result.ruleId}
                    className={`flex items-start space-x-2 text-sm ${
                      result.severity === 'error' ? 'text-red-700' :
                      result.severity === 'warning' ? 'text-yellow-700' : 'text-green-700'
                    }`}
                  >
                    {result.severity === 'error' ? (
                      <AlertTriangle className="w-4 h-4 mt-0.5" />
                    ) : result.severity === 'warning' ? (
                      <Info className="w-4 h-4 mt-0.5" />
                    ) : (
                      <CheckCircle className="w-4 h-4 mt-0.5" />
                    )}
                    <span>{result.message || result.ruleId}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Draft management */}
      {draftable && (
        <div className="relative">
          <button
            onClick={() => setShowDrafts(!showDrafts)}
            className={`
              ${buttonBaseClass}
              ${isDirty ? 'bg-yellow-100 border-yellow-300 text-yellow-700' : secondaryButtonClass}
            `}
            title="Draft management"
          >
            <History className="w-4 h-4" />
            {isDirty && <span className="ml-1 text-xs">*</span>}
          </button>

          {showDrafts && (
            <div className="absolute top-full right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-3 z-50 min-w-48">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Draft Management</h4>
              <div className="space-y-2">
                {onSaveDraft && (
                  <button
                    onClick={() => {
                      onSaveDraft();
                      setShowDrafts(false);
                    }}
                    disabled={!isDirty}
                    className="w-full px-3 py-2 text-sm text-left bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    <Save className="w-3 h-3 inline mr-2" />
                    Save Current State
                  </button>
                )}

                {savedDrafts.length > 0 && (
                  <>
                    <hr className="my-2" />
                    <div className="text-xs text-gray-500 mb-1">Saved Drafts</div>
                    {savedDrafts.slice(0, 5).map(draft => (
                      <button
                        key={draft.id}
                        onClick={() => {
                          onLoadDraft?.();
                          setShowDrafts(false);
                        }}
                        className="w-full px-2 py-1 text-sm text-left text-gray-700 hover:bg-gray-100 rounded"
                      >
                        <div className="font-medium">{draft.name}</div>
                        <div className="text-xs text-gray-500">
                          {new Date(draft.updatedAt).toLocaleDateString()}
                        </div>
                      </button>
                    ))}
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );

  return (
    <div className={`flex ${orientation === 'vertical' ? 'flex-col' : 'flex-row'} items-center space-${orientation === 'vertical' ? 'y' : 'x'}-3 ${className}`}>
      {/* Progress indicator */}
      {showProgress && progressTarget && (
        <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${Math.min(100, progressPercentage)}%` }}
          />
          <div className="text-xs text-center text-gray-600 mt-1">
            {Math.round(progress)} / {progressTarget} ({Math.round(progressPercentage)}%)
          </div>
        </div>
      )}

      {/* Transfer mode indicator */}
      {copyMode && (
        <div className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full mb-2">
          Copy Mode
        </div>
      )}

      {/* Main transfer buttons */}
      <div className={`flex ${orientation === 'vertical' ? 'flex-col' : 'flex-row'} space-${orientation === 'vertical' ? 'y' : 'x'}-2`}>
        {transferButtons}
      </div>

      {/* Utility buttons */}
      {(allowCopy || undoable || onToggleAutoTransfer) && (
        <div className={`flex ${orientation === 'vertical' ? 'flex-col' : 'flex-row'} space-${orientation === 'vertical' ? 'y' : 'x'}-2`}>
          {utilityButtons}
        </div>
      )}

      {/* Status and management buttons */}
      <div className={`flex ${orientation === 'vertical' ? 'flex-col' : 'flex-row'} space-${orientation === 'vertical' ? 'y' : 'x'}-2`}>
        {statusButtons}
      </div>

      {/* Click outside handlers */}
      {showValidation && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowValidation(false)}
        />
      )}

      {showDrafts && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowDrafts(false)}
        />
      )}
    </div>
  );
}