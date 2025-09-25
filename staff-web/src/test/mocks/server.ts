/**
 * MSW server setup for testing
 */

import { setupServer } from 'msw/node';
import { handlers } from './handlers';

// Setup requests interception with the handlers
export const server = setupServer(...handlers);