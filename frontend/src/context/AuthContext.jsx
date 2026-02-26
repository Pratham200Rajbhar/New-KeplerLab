import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { login as apiLogin, signup as apiSignup, logout as apiLogout, getCurrentUser, refreshToken } from '../api/auth';
import { setAccessToken as syncTokenToApi } from '../api/config';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [accessToken, setAccessToken] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const refreshTimerRef = useRef(null);
    const accessTokenRef = useRef(null);
    const isInitializingRef = useRef(false); // Prevent duplicate init calls

    // Keep config.js and ref in sync with current access token
    useEffect(() => {
        syncTokenToApi(accessToken);
        accessTokenRef.current = accessToken;
    }, [accessToken]);

    // Schedule silent token refresh before expiry (every 13 min for 15 min token)
    const scheduleRefresh = useCallback(() => {
        if (refreshTimerRef.current) {
            clearTimeout(refreshTimerRef.current);
        }
        refreshTimerRef.current = setTimeout(async () => {
            try {
                const tokens = await refreshToken();
                setAccessToken(tokens.access_token);
                scheduleRefresh();
            } catch {
                // Refresh failed — session expired
                setAccessToken(null);
                setUser(null);
            }
        }, 13 * 60 * 1000); // 13 minutes
    }, []);

    // On mount: try to silently refresh (cookie-based)
    useEffect(() => {
        const initAuth = async () => {
            // Prevent duplicate concurrent calls
            if (isInitializingRef.current) {
                return;
            }

            isInitializingRef.current = true;
            try {
                // Try to get a fresh access token using the refresh cookie
                const tokens = await refreshToken();
                setAccessToken(tokens.access_token);

                // Get user data with the new access token
                const userData = await getCurrentUser(tokens.access_token);
                setUser(userData);

                scheduleRefresh();
            } catch (error) {
                setAccessToken(null);
                setUser(null);
            } finally {
                setIsLoading(false);
                isInitializingRef.current = false;
            }
        };
        initAuth();

        return () => {
            if (refreshTimerRef.current) {
                clearTimeout(refreshTimerRef.current);
            }
        };
    }, []); // Run only once on mount - scheduleRefresh is stable

    const login = useCallback(async (email, password) => {
        setError(null);
        try {
            const tokens = await apiLogin(email, password);
            setAccessToken(tokens.access_token);
            const userData = await getCurrentUser(tokens.access_token);
            setUser(userData);
            scheduleRefresh();
            return true;
        } catch (err) {
            setError(err.message || 'Login failed');
            return false;
        }
    }, [scheduleRefresh]);

    const signup = useCallback(async (email, username, password) => {
        setError(null);
        try {
            await apiSignup(email, username, password);
            return true;
        } catch (err) {
            setError(err.message || 'Signup failed');
            return false;
        }
    }, []);

    const logout = useCallback(async () => {
        try {
            // Use ref to avoid stale closure capturing old accessToken
            await apiLogout(accessTokenRef.current);
        } catch {
            // Ignore logout errors
        }
        if (refreshTimerRef.current) {
            clearTimeout(refreshTimerRef.current);
        }
        setAccessToken(null);
        setUser(null);
    }, []);

    const value = {
        user,
        accessToken,
        isAuthenticated: !!user,
        isLoading,
        error,
        login,
        signup,
        logout,
        setError,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
