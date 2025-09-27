import React from 'react';
import { render, fireEvent, screen } from '@testing-library/react-native';
import { Button } from 'react-native-paper';

describe('Button Component', () => {
  it('renders correctly with title', () => {
    render(<Button mode="contained">Test Button</Button>);
    expect(screen.getByText('Test Button')).toBeDefined();
  });

  it('handles press events', () => {
    const mockOnPress = jest.fn();
    render(
      <Button mode="contained" onPress={mockOnPress}>
        Clickable Button
      </Button>
    );

    fireEvent.press(screen.getByText('Clickable Button'));
    expect(mockOnPress).toHaveBeenCalledTimes(1);
  });

  it('shows loading state when disabled', () => {
    render(
      <Button mode="contained" loading disabled>
        Loading Button
      </Button>
    );

    const button = screen.getByText('Loading Button');
    expect(button.props.accessibilityState?.disabled).toBe(true);
  });
});