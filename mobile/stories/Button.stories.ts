import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import { Button } from 'react-native-paper';

// More on how to set up stories at: https://storybook.js.org/docs/writing-stories#default-export
const meta: Meta<typeof Button> = {
  title: 'NAGA Mobile/Components/Button',
  component: Button,
  parameters: {
    // Optional parameter to center the component in the Canvas. More info: https://storybook.js.org/docs/configure/story-layout
    layout: 'centered',
  },
  // This component will have an automatically generated Autodocs entry: https://storybook.js.org/docs/writing-docs/autodocs
  tags: ['autodocs'],
  // More on argTypes: https://storybook.js.org/docs/api/argtypes
  argTypes: {
    mode: {
      control: 'select',
      options: ['contained', 'outlined', 'text'],
    },
    disabled: {
      control: 'boolean',
    },
  },
  // Use `fn` to spy on the onClick arg, which will appear in the actions panel once invoked: https://storybook.js.org/docs/essentials/actions#action-args
  args: { onPress: fn() },
};

export default meta;
type Story = StoryObj<typeof meta>;

// More on writing stories with args: https://storybook.js.org/docs/writing-stories/args
export const Primary: Story = {
  args: {
    mode: 'contained',
    children: 'Sign In',
  },
};

export const Secondary: Story = {
  args: {
    mode: 'outlined',
    children: 'Cancel',
  },
};

export const Text: Story = {
  args: {
    mode: 'text',
    children: 'Forgot Password?',
  },
};

export const Loading: Story = {
  args: {
    mode: 'contained',
    children: 'Processing...',
    loading: true,
  },
};

export const Disabled: Story = {
  args: {
    mode: 'contained',
    children: 'Submit',
    disabled: true,
  },
};

export const WithIcon: Story = {
  args: {
    mode: 'contained',
    children: 'Login with Google',
    icon: 'google',
  },
};