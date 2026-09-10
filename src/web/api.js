async function getProfileInfo() {
    try {
        const response = await fetch("/api/user-info");
        if (!response.ok) {
            throw new Error(`Response status: ${response.status}`);
        }
        const result = await response.json();
                
        // will always have a value from my backend
        let photoURL = result.photo_url;
        let name = result.name;

        const profileImg = document.getElementById("profile-photo");
        profileImg.src = photoURL;

        const nameTitle = document.getElementById("profile-name");
        nameTitle.textContent = name;
    }
    catch (error) {
        console.log(error.message);
    }
}

getProfileInfo();