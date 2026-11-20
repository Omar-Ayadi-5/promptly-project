import { API_BASE_URL } from '../api';
import "./settingsStyle.css"
import { useAuth } from "../authContext"


function Settings(){

    const {userId, userEmail, token}= useAuth();


    const handleDelete  = async () =>{
        if (!window.confirm("Delete your account and all saved conversations? This cannot be undone.")) return;
        try{
        const response = await fetch(`${API_BASE_URL}/api/Delete_account`,
            {
                method : "DELETE",
                headers : {
                    "authorization" : `bearer ${token}`,
                    "content-type": "application/json"
                },
                body:JSON.stringify({user_id : userId})
            })
        const data = await response.json()
        if(data.confirmed === "deleted"){
            alert("account deleted successfuly");
            localStorage.removeItem("authToken");
            window.location.href = "/";
        }
        else{
            window.alert(data.error || "Unable to delete your account. Please try again.");
            return;
        }

        }catch(error){
            console.error("Failed to get model details:", error);
            return;
        }

    }

    return (
        <div className="settings-container">
            <h2>Account Settings</h2>
            <p><strong>Current Email:</strong> {userEmail}</p>
            <button className="delete-account-btn" onClick={handleDelete}>
                Delete Account
            </button>
        </div>
    )
}
export default Settings;
