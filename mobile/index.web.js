import { AppRegistry } from 'react-native';
import App from './App';
import { name as appName } from './package.json';

// Register the app for web
AppRegistry.registerComponent(appName, () => App);

// Mount the app to the DOM
AppRegistry.runApplication(appName, {
    rootTag: document.getElementById('root'),
});