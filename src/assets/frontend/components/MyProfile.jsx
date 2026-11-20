import { API_BASE_URL } from '../api';
import React, { useState } from "react";
import "./MyProfile.css";
import { useAuth } from "../authContext";


function MyProfile() {
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmNewPassword, setConfirmNewPassword] = useState("");
    const [message, setMessage] = useState("");
    const {userId, userEmail, token}= useAuth();


    const submitNewPassword = async () => {
        const response = await fetch(`${API_BASE_URL}/api/change_password`, {
            method: 'POST',
            headers: {
                "authorization":`bearer ${token}`,
                'content-type': "application/json" },
            body: JSON.stringify({
                currentPassword: currentPassword,
                newPassword: newPassword,
                userEmail: userEmail,
                userId : userId
            })
        })
        if (!response.ok) {
            setMessage("An error occurred while changing the password.");
            throw new Error("An error occurred while changing the password.");
        }
        const data = await response.json();
        if (data.confirm == "Current password is incorrect") {
            setMessage("Current password is incorrect.");
            throw new Error("Current password incorrect");
        }
        else if ( data.confirm == "confirmed"){
                setMessage("Password changed successfully!");
                setCurrentPassword("");
                setNewPassword("");
                setConfirmNewPassword("");
            }
        else {
            setMessage("An error occurred while changing the password.");
            throw new Error("An error occurred while changing the password.");
        }
    }

    const handleChangePassword = async (e) => {
        e.preventDefault();

        if (newPassword !== confirmNewPassword) {
            setMessage("New passwords do not match.");
            return;
        }
        else if(newPassword == currentPassword){
            setMessage("Can't change to the same password.");
            return;
        }

        try {
            await submitNewPassword();
        } catch (error) {
            console.error(error);
        }
    };


    return (
        <div className="profile-container">
            <h2>My Profile</h2>
            <p><strong>Current Email  :  </strong> {userEmail}</p>

            <h3>Change Password</h3>
            <form onSubmit={handleChangePassword} className="password-form">
                <label>
                    Current Password:
                    <input
                        type="password"
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        required
                    />
                </label>

                <label>
                    New Password:
                    <input
                        type="password"
                        value={newPassword}
                        minLength={12}
                        maxLength={128}
                        autoComplete="new-password"
                        onChange={(e) => setNewPassword(e.target.value)}
                        required
                    />
                </label>

                <label>
                    Confirm New Password:
                    <input
                        type="password"
                        value={confirmNewPassword}
                        onChange={(e) => setConfirmNewPassword(e.target.value)}
                        required
                    />
                </label>

                <button type="submit" >Update Password</button>
            </form>

            {message && <p className="profile-message">{message}</p>}
        </div>
    );
}

export default MyProfile;
