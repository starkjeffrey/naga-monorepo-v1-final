/**
 * Google Sign-In Button for Mobile Authentication
 *
 * Provides a secure Google Sign-In button for React Native/Expo applications
 * with proper error handling and loading states.
 */

import React, { useState } from 'react'
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
  Platform,
} from 'react-native'
import * as Google from 'expo-auth-session/providers/google'
import * as WebBrowser from 'expo-web-browser'
import * as Device from 'expo-device'
import { mobileAuth, type GoogleAuthCredentials } from '../../services/mobileAuth'
import { getAuthConfig, getCdnConfig } from '../../config/env'
import type { GoogleUserProfile, GoogleAuthResponse } from '../../types/errors'

// Configure WebBrowser for Google Auth
WebBrowser.maybeCompleteAuthSession()

interface GoogleSignInButtonProps {
  onSuccess?: (authData: GoogleAuthResponse) => void
  onError?: (error: string) => void
  disabled?: boolean
  style?: React.ComponentProps<typeof TouchableOpacity>['style']
}

export const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({
  onSuccess,
  onError,
  disabled = false,
  style,
}) => {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Google Auth configuration
  const authConfig = getAuthConfig()
  const [request, response, promptAsync] = Google.useAuthRequest({
    expoClientId: process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID,
    iosClientId: process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID,
    androidClientId: process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID,
    webClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID,
    scopes: ['openid', 'profile', 'email'],
    additionalParameters: {
      hd: authConfig.allowedEmailDomain, // Restrict to configured domain
    },
  })

  // Handle Google Auth response
  React.useEffect(() => {
    if (response?.type === 'success') {
      handleGoogleAuthSuccess(response)
    } else if (response?.type === 'error') {
      handleGoogleAuthError(response.error)
    }
  }, [response])

  /**
   * Handle successful Google authentication
   */
  const handleGoogleAuthSuccess = async (
    authResponse: Google.AuthSessionResult & { type: 'success' }
  ) => {
    try {
      setIsLoading(true)
      setError(null)

      // Extract user info from Google response
      const cdnConfig = getCdnConfig()
      const userInfoResponse = await fetch(
        `${cdnConfig.googleApisBaseUrl}/userinfo/v2/me?access_token=${authResponse.authentication.accessToken}`
      )

      if (!userInfoResponse.ok) {
        throw new Error('Failed to get user information from Google')
      }

      const userInfo = (await userInfoResponse.json()) as GoogleUserProfile

      // Validate email domain
      const allowedDomain = `@${authConfig.allowedEmailDomain}`
      if (!userInfo.email?.endsWith(allowedDomain)) {
        throw new Error(`Please use your ${allowedDomain} email address`)
      }

      // Create credentials object
      const credentials: GoogleAuthCredentials = {
        idToken: authResponse.authentication.idToken,
        accessToken: authResponse.authentication.accessToken,
        user: {
          email: userInfo.email,
          name: userInfo.name,
          picture: userInfo.picture,
          id: userInfo.id,
        },
      }

      // Get device ID
      const deviceId = await getDeviceId()

      // Authenticate with backend
      const result = await mobileAuth.authenticateWithGoogle(credentials, deviceId)

      if (result.success) {
        onSuccess?.(result)
      } else {
        throw new Error(result.error || 'Authentication failed')
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Authentication failed'
      setError(errorMessage)
      onError?.(errorMessage)

      Alert.alert('Authentication Failed', errorMessage, [{ text: 'OK' }])
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * Handle Google authentication error
   */
  const handleGoogleAuthError = (error: unknown) => {
    console.error('Google Auth Error:', error)

    let errorMessage = 'Google authentication failed'

    if (
      error &&
      typeof error === 'object' &&
      'message' in error &&
      typeof error.message === 'string'
    ) {
      errorMessage = error.message
    } else if (typeof error === 'string') {
      errorMessage = error
    }

    setError(errorMessage)
    onError?.(errorMessage)

    Alert.alert('Authentication Error', errorMessage, [{ text: 'OK' }])
  }

  /**
   * Get unique device identifier
   */
  const getDeviceId = async (): Promise<string> => {
    try {
      // Get device name and model
      const deviceName = Device.deviceName || 'Unknown Device'
      const modelName = Device.modelName || 'Unknown Model'
      const platform = Platform.OS

      // Create a unique identifier
      const deviceId = `${platform}-${modelName}-${deviceName}`.replace(/[^a-zA-Z0-9-]/g, '')

      return deviceId
    } catch (error) {
      console.error('Failed to get device ID:', error)
      return `${Platform.OS}-unknown-${Date.now()}`
    }
  }

  /**
   * Handle sign in button press
   */
  const handleSignIn = async () => {
    try {
      setError(null)

      if (!request) {
        throw new Error('Google Auth not configured properly')
      }

      await promptAsync()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start authentication'
      setError(errorMessage)
      onError?.(errorMessage)

      Alert.alert('Error', errorMessage, [{ text: 'OK' }])
    }
  }

  return (
    <View style={[styles.container, style]}>
      <TouchableOpacity
        style={[
          styles.button,
          disabled && styles.buttonDisabled,
          isLoading && styles.buttonLoading,
        ]}
        onPress={handleSignIn}
        disabled={disabled || isLoading || !request}
        activeOpacity={0.8}
      >
        {isLoading ? (
          <ActivityIndicator color="#fff" size="small" />
        ) : (
          <>
            <GoogleIcon />
            <Text style={styles.buttonText}>Sign in with Google</Text>
          </>
        )}
      </TouchableOpacity>

      {error && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}
    </View>
  )
}

/**
 * Google Icon Component
 */
const GoogleIcon: React.FC = () => (
  <View style={styles.iconContainer}>
    <Text style={styles.iconText}>G</Text>
  </View>
)

const styles = StyleSheet.create({
  container: {
    width: '100%',
    alignItems: 'center',
  },
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#4285F4',
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 12,
    minWidth: 200,
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  buttonDisabled: {
    backgroundColor: '#cccccc',
    shadowOpacity: 0,
    elevation: 0,
  },
  buttonLoading: {
    backgroundColor: '#3367D6',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  iconContainer: {
    width: 20,
    height: 20,
    backgroundColor: '#fff',
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconText: {
    color: '#4285F4',
    fontSize: 14,
    fontWeight: 'bold',
  },
  errorContainer: {
    marginTop: 12,
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#ffebee',
    borderRadius: 4,
    borderLeftWidth: 4,
    borderLeftColor: '#f44336',
  },
  errorText: {
    color: '#d32f2f',
    fontSize: 14,
    textAlign: 'center',
  },
})

export default GoogleSignInButton
