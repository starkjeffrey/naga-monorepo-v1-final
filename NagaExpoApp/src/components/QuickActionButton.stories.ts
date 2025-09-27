import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import QuickActionButton from './QuickActionButton';

const meta: Meta<typeof QuickActionButton> = {
  title: 'NAGA Mobile/Components/QuickActionButton',
  component: QuickActionButton,
  parameters: {
    layout: 'centered',
    backgrounds: { default: 'mobile' },
  },
  tags: ['autodocs'],
  argTypes: {
    color: {
      control: 'color',
      description: 'Button background color',
    },
    icon: {
      control: 'text',
      description: 'Material Community Icons icon name',
    },
    title: {
      control: 'text',
      description: 'Button text',
    },
    disabled: {
      control: 'boolean',
      description: 'Disable button interaction',
    },
    loading: {
      control: 'boolean',
      description: 'Show loading spinner',
    },
  },
  args: { onPress: fn() },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    title: 'View Attendance',
    icon: 'calendar-check',
    color: '#4CAF50',
  },
};

export const Grades: Story = {
  args: {
    title: 'Check Grades',
    icon: 'school',
    color: '#2196F3',
  },
};

export const Schedule: Story = {
  args: {
    title: 'My Schedule',
    icon: 'timetable',
    color: '#FF9800',
  },
};

export const Finances: Story = {
  args: {
    title: 'Finances',
    icon: 'cash',
    color: '#9C27B0',
  },
};

export const Loading: Story = {
  args: {
    title: 'Processing',
    icon: 'loading',
    color: '#4CAF50',
    loading: true,
  },
};

export const Disabled: Story = {
  args: {
    title: 'Unavailable',
    icon: 'lock',
    color: '#9E9E9E',
    disabled: true,
  },
};

export const CustomColor: Story = {
  args: {
    title: 'Messages',
    icon: 'message',
    color: '#E91E63',
  },
};