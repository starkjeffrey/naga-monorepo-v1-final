# NAGA Mobile App - Storybook

Component development environment for the NAGA React Native mobile application.

## Overview

Storybook allows you to:
- **Develop components in isolation** - Test individual components without running the full app
- **Document component APIs** - Automatic documentation generation with controls
- **Visual testing** - See all component states and variations
- **Share components** - Easy way to share components with designers and stakeholders

## Getting Started

### Install Dependencies
```bash
cd mobile
npm install
```

### Run Storybook
```bash
# Start Storybook development server
npm run storybook

# Opens at http://localhost:6006
```

### Build Storybook (for deployment)
```bash
npm run build-storybook
```

## Project Structure
```
mobile/
├── .storybook/           # Storybook configuration
│   ├── main.ts          # Main config file
│   └── preview.ts       # Global decorators and parameters
├── stories/             # Example stories and documentation
│   ├── Introduction.stories.mdx
│   └── Button.stories.ts
└── src/
    └── components/      # Component stories live next to components
        ├── QuickActionButton.tsx
        └── QuickActionButton.stories.ts
```

## Writing Stories

### Basic Component Story
```typescript
import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import MyComponent from './MyComponent';

const meta: Meta<typeof MyComponent> = {
  title: 'NAGA Mobile/Components/MyComponent',
  component: MyComponent,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  args: { onPress: fn() },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    title: 'Default Example',
  },
};

export const Loading: Story = {
  args: {
    title: 'Loading State',
    loading: true,
  },
};
```

## Available Components

### UI Components
- **QuickActionButton** - Colorful action buttons with icons
- **ErrorBoundary** - Error handling wrapper
- *(More components to be added)*

### Screen Components
- **Login Screen** - Authentication form
- **Dashboard Screen** - Main dashboard layout
- **Profile Screen** - User profile management
- *(More screens to be added)*

## Component Categories

### Authentication
- Login forms
- Registration forms
- Auth validation components

### Navigation
- Tab bar components
- Navigation buttons
- Route components

### Data Display
- Cards
- Lists
- Tables
- Charts

### Forms & Input
- Text inputs
- Buttons
- Checkboxes
- Date pickers

### Feedback
- Loading indicators
- Error messages
- Success alerts
- Progress bars

## Best Practices

### Story Organization
```
- Use consistent naming: `ComponentName.stories.ts`
- Group related stories under same title prefix
- Include comprehensive examples (default, loading, error, etc.)
- Add interactive controls for key props
- Write clear documentation
```

### Component Documentation
```typescript
// Include JSDoc comments for automatic documentation
/**
 * QuickActionButton provides a colorful action button with icon
 *
 * @param title - Button text label
 * @param icon - Material Community Icons name
 * @param color - Button background color
 * @param onPress - Click handler function
 */
```

### Controls and Args
```typescript
argTypes: {
  color: {
    control: 'color',
    description: 'Button background color',
  },
  disabled: {
    control: 'boolean',
    description: 'Disable button interaction',
  },
}
```

## Development Workflow

1. **Create Component** - Build React Native component
2. **Write Story** - Create comprehensive story file
3. **Test Variations** - Use Storybook controls to test all states
4. **Document** - Add descriptions and usage examples
5. **Share** - Use Storybook URL to share with team

## Integration with React Native

### Mock Navigation
For components that use React Navigation, use mock navigation in stories:
```typescript
// Mock navigation prop for stories
const mockNavigation = {
  navigate: fn(),
  goBack: fn(),
  // ... other navigation methods
};
```

### Mock State
For components using Zustand or other state management:
```typescript
// Create mock store for stories
const mockStore = {
  user: { name: 'John Doe', email: 'john@example.com' },
  isAuthenticated: true,
};
```

## Deployment

Storybook can be deployed to:
- **Netlify** - Static hosting
- **GitHub Pages** - Free hosting for open source
- **AWS S3** - Enterprise hosting
- **Chromatic** - Visual regression testing

```bash
# Build for deployment
npm run build-storybook

# Output goes to storybook-static/
```

## Tips

- **Use backgrounds addon** - Test components on different backgrounds
- **Include edge cases** - Empty states, long text, error states
- **Mobile viewport** - Test responsive behavior
- **Accessibility** - Use accessibility addon to test a11y
- **Visual regression** - Use Chromatic for automated visual testing

## Resources

- [Storybook Documentation](https://storybook.js.org/docs)
- [React Native Storybook](https://storybook.js.org/docs/react/get-started/introduction)
- [Writing Stories](https://storybook.js.org/docs/react/writing-stories/introduction)