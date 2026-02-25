import { useState } from 'react';
import Login from './Login';
import Signup from './Signup';

export default function AuthPage() {
    const [showLogin, setShowLogin] = useState(true);

    return showLogin ? (
        <Login onSwitchToSignup={() => setShowLogin(false)} />
    ) : (
        <Signup onSwitchToLogin={() => setShowLogin(true)} />
    );
}
