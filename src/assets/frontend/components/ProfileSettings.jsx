import "./ProfileSettings.css";
import { useNavigate } from "react-router-dom";


function ShowProfile() {
  const navigate = useNavigate();


  const handleMyProfile= () =>{
        navigate("/MyProfile");
      }
  const handleSettings = () =>{
      navigate("/settings");
  }
  const onLogout= () => {
    localStorage.removeItem("authToken");
    window.location.href = "/";
  }

  return (
    <div className="profile-dropdown">
      <ul>
        <li><button onClick={onLogout}>Log out</button></li>
        <li><button onClick={handleSettings}>Settings</button></li>
        <li><button onClick={handleMyProfile}>My profile</button></li>
      </ul>
    </div>
  );
}

export default ShowProfile;
