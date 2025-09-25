# TransferList Component Demo

## 🎯 View the Demo

1. **Start the dev server:**
   ```bash
   cd /Volumes/Projects/naga-monorepo-v1-final/staff-web
   npm run dev
   ```

2. **Open the demo in your browser:**
   ```
   http://localhost:5173/demo/transfer-list
   ```

## 📁 Component Files

- **Main Component**: `src/components/TransferList.tsx`
- **Demo Page**: `src/pages/TransferListDemo.tsx`
- **Route Added**: `/demo/transfer-list`

## ✨ Features Showcased

### Student Enrollment Management
- Move students between "Available" and "Enrolled" lists
- Search by name, email, or student ID
- Multi-select with checkboxes
- Bulk operations (move all)

### Permission Management
- Assign permissions to users or roles
- Same transfer mechanics, different data
- Shows versatility of the component

### Arrow Controls
- `>>` Move ALL items from left to right
- `>` Move SELECTED items from left to right
- `<` Move SELECTED items from right to left
- `<<` Move ALL items from right to left

## 🔧 Usage in Your App

```tsx
import TransferList, { TransferItem } from './components/TransferList';

const MyComponent = () => {
  const [available, setAvailable] = useState<TransferItem[]>([...]);
  const [enrolled, setEnrolled] = useState<TransferItem[]>([...]);

  const handleChange = (newAvailable: TransferItem[], newEnrolled: TransferItem[]) => {
    // Handle the transfer
    console.log('Available:', newAvailable.length);
    console.log('Enrolled:', newEnrolled.length);
  };

  return (
    <TransferList
      availableItems={available}
      enrolledItems={enrolled}
      availableTitle="Available Students"
      enrolledTitle="Enrolled Students"
      onChange={handleChange}
    />
  );
};
```

## 🎨 Styling

- Uses Ant Design components and styling
- Tailwind CSS for custom styling
- Fully responsive (mobile/desktop)
- Clean, professional appearance

## 🔄 Real-world Applications

- **Student Enrollment**: Class/program enrollment management
- **Permission Management**: User role and permission assignment
- **Group Membership**: Adding/removing users from groups
- **Category Assignment**: Product categorization, tagging
- **Resource Allocation**: Assigning resources to projects/users

The component is completely reusable and can work with any data that has an `id` and `name` property!