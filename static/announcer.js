const messages = [
    "THE DUNGEON ACKNOWLEDGES YOUR EXISTENCE.",
    "A CRAWLER HAS BEEN MODIFIED. AUDIENCE ENGAGEMENT INCREASED.",
    "STAT ALTERATION DETECTED. THE SYSTEM APPROVES… OR DOES IT?",
    "EQUIPMENT SYNC COMPLETE. REALITY STABILITY: COMPROMISED.",
    "YOU ARE BEING BROADCAST TO 3.7 BILLION VIEWERS.",
    "THE AI IS WATCHING. IT IS ALWAYS WATCHING.",
    "BUFF REGISTERED. BALANCE ADJUSTMENTS PENDING… PROBABLY."
];

function announce(msg) {
    const box = document.getElementById("announcer");
    box.innerText = msg;
}

function randomAnnouncement() {
    const msg = messages[Math.floor(Math.random() * messages.length)];
    announce(msg);
}

setInterval(randomAnnouncement, 8000);
