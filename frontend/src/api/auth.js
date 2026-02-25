import { apiConfig } from './config';

const API_BASE = apiConfig.baseUrl;

export async function login(email, password) {
    const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Invalid email or password');
    }

    // Returns { access_token, token_type }
    // Refresh token is set as HttpOnly cookie automatically
    return response.json();
}

export async function signup(email, username, password) {
    const response = await fetch(`${API_BASE}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, username, password }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Signup failed');
    }

    return response.json();
}

export async function logout(accessToken) {
    await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`,
        },
    }).catch(() => { });
}

export async function getCurrentUser(accessToken) {
    if (!accessToken) {
        throw new Error('No access token');
    }

    const response = await fetch(`${API_BASE}/auth/me`, {
        headers: {
            'Authorization': `Bearer ${accessToken}`,
        },
    });

    if (!response.ok) {
        throw new Error('Failed to get user');
    }

    return response.json();
}

export async function refreshToken() {
    // Uses HttpOnly cookie — no token in body or localStorage
    const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
        throw new Error('Token refresh failed');
    }

    // Returns { access_token, token_type }
    return response.json();
}
