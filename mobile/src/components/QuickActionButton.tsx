import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Button, Text } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

export interface QuickActionButtonProps {
  title: string;
  icon: string;
  color?: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
}

const QuickActionButton: React.FC<QuickActionButtonProps> = ({
  title,
  icon,
  color = '#2196F3',
  onPress,
  disabled = false,
  loading = false,
}) => {
  return (
    <View style={styles.container}>
      <Button
        mode="contained"
        buttonColor={color}
        style={styles.button}
        contentStyle={styles.buttonContent}
        icon={() => <Icon name={icon} size={24} color="white" />}
        onPress={onPress}
        disabled={disabled}
        loading={loading}
      >
        {loading ? '' : title}
      </Button>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    minWidth: 150,
    margin: 4,
  },
  button: {
    borderRadius: 12,
  },
  buttonContent: {
    paddingVertical: 12,
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
  },
});

export default QuickActionButton;