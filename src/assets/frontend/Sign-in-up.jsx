import { useState } from 'react';
import { API_BASE_URL } from './api';
import './sign-in-up-style.css';

export default function AuthForm() {
  const [isSignUp, setIsSignUp] = useState(false);
  const [step, setStep] = useState('form');
  const [formData, setFormData] = useState({ email: '', password: '', confirmPassword: '' });
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function post(path, body) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || 'Something went wrong. Please try again.');
    return data;
  }

  function toggle() {
    setIsSignUp(value => !value);
    setStep('form');
    setFormData({ email: '', password: '', confirmPassword: '' });
    setCode(''); setError(''); setNotice('');
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError(''); setNotice('');
    try {
      if (!isSignUp) {
        const data = await post('/api/sign_in', { email: formData.email.trim(), password: formData.password });
        if (!data.token) throw new Error('Invalid email or password.');
        localStorage.setItem('authToken', data.token);
        window.location.assign('/app');
      } else if (step === 'form') {
        if (formData.password !== formData.confirmPassword) throw new Error('Passwords do not match.');
        await post('/api/send_code', { email: formData.email.trim() });
        setStep('verify');
        setNotice('A verification code is on its way. Check your inbox and spam folder.');
      } else {
        await post('/api/sign_up', { email: formData.email.trim(), password: formData.password, code });
        setIsSignUp(false); setStep('form'); setCode('');
        setFormData(previous => ({ ...previous, password: '', confirmPassword: '' }));
        setNotice('Your account is ready. Sign in to start a conversation.');
      }
    } catch (failure) {
      setError(failure instanceof TypeError ? 'Unable to connect. Please try again shortly.' : failure.message);
    } finally { setBusy(false); }
  }

  const change = event => setFormData(previous => ({ ...previous, [event.target.name]: event.target.value }));
  return (
    <div className="auth-container">
      <div className="auth-story">
        <a className="wordmark" href="/" aria-label="Promptly home"><span className="brand-mark">P</span>Promptly<span className="brand-dot">.</span></a>
        <span className="eyebrow">A LITTLE CURIOSITY. A NEW PERSPECTIVE.</span>
        <h1>Good questions.<br /><span>Better conversations.</span></h1>
        <p>A focused space to think with AI. Choose your model, shape its response, and keep your ideas moving.</p>
        <div className="auth-feature-list">
          <div><span>01</span><p><strong>More than one perspective</strong>Explore different AI models in one workspace.</p></div>
          <div><span>02</span><p><strong>A response that fits</strong>Adjust model settings to suit the task.</p></div>
          <div><span>03</span><p><strong>Room to keep thinking</strong>Return to saved chats or ask a question by voice.</p></div>
        </div>
        <p className="auth-footnote">Built for the next question.</p>
      </div>
      <div className="auth-card-wrap">
        <form className="auth-form" onSubmit={handleSubmit}>
          <span className="eyebrow">YOUR NEXT IDEA STARTS HERE</span>
          <h2>{isSignUp ? (step === 'verify' ? 'Check your inbox' : 'Create your workspace') : 'Welcome back'}</h2>
          <p className="auth-description">{isSignUp ? (step === 'verify' ? `Enter the code sent to ${formData.email}. It expires in 10 minutes.` : 'Make a little space for your next big idea.') : 'Sign in to pick up the conversation.'}</p>
          {error && <p className="form-error" role="alert">{error}</p>}
          {notice && <p className="form-notice" role="status">{notice}</p>}
          {isSignUp && step === 'verify' ? (
            <label>Verification code<input name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={event => setCode(event.target.value)} placeholder="000000" required autoFocus /></label>
          ) : (
            <>
              <label>Email address<input type="email" name="email" autoComplete="email" value={formData.email} onChange={change} placeholder="you@example.com" maxLength={254} required /></label>
              <label>Password<input type="password" name="password" autoComplete={isSignUp ? 'new-password' : 'current-password'} minLength={isSignUp ? 12 : 1} maxLength={128} value={formData.password} onChange={change} placeholder={isSignUp ? 'At least 12 characters' : 'Enter your password'} required /></label>
              {isSignUp && <label>Confirm password<input type="password" name="confirmPassword" autoComplete="new-password" minLength={12} maxLength={128} value={formData.confirmPassword} onChange={change} placeholder="Repeat your password" required /></label>}
            </>
          )}
          <button type="submit" className="auth-button" disabled={busy}>{busy ? 'Please wait...' : isSignUp ? (step === 'verify' ? 'Verify and create account' : 'Continue with email') : 'Sign in'}<span aria-hidden="true"> &rarr;</span></button>
          {step === 'verify' ? <button type="button" className="toggle-link" onClick={() => { setStep('form'); setCode(''); setError(''); setNotice(''); }} disabled={busy}>Use a different email or request a new code</button> : <p className="toggle-text">{isSignUp ? 'Already have an account?' : 'New to Promptly?'} <button type="button" className="toggle-link" onClick={toggle} disabled={busy}>{isSignUp ? 'Sign in' : 'Create an account'}</button></p>}
        </form>
      </div>
    </div>
  );
}
