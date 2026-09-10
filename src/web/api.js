async function getProfileInfo() {
    try {
        const response = await fetch("/api/user-info");
        if (!response.ok) {
            throw new Error(`Response status: ${response.status}`);
        }
        const result = await response.json();
    }
    catch (error) {
        console.log(error.message);
    }
}

getProfileInfo();