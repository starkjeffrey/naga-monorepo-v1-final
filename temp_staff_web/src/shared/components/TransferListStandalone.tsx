/**
 * Standalone TransferList Demo
 * This can be used directly without routing if needed
 */

import React from 'react';
import { ConfigProvider, App as AntdApp } from 'antd';
import { TransferListDemo } from '../pages/TransferListDemo';

// Ant Design theme configuration
const theme = {
  token: {
    colorPrimary: '#1890ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#f5222d',
    colorBgContainer: '#ffffff',
    colorBgLayout: '#f0f2f5',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    fontSize: 14,
    borderRadius: 6,
  },
  components: {
    Button: {
      borderRadius: 6,
    },
    Input: {
      borderRadius: 6,
    },
    Card: {
      borderRadius: 8,
    },
  },
};

export const StandaloneDemo: React.FC = () => {
  return (
    <ConfigProvider theme={theme}>
      <AntdApp>
        <TransferListDemo />
      </AntdApp>
    </ConfigProvider>
  );
};

export default StandaloneDemo;