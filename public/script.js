document.addEventListener('DOMContentLoaded', () => { // Ensures the DOM is fully loaded before running the script
    // 1. Initial setup
    const gameContainer = document.getElementById('gameContainer');

    const backgroundCanvas = document.getElementById('backgroundCanvas');
    const gameCanvas = document.getElementById('gameCanvas');

    const bCtx = backgroundCanvas.getContext('2d');
    const ctx = gameCanvas.getContext('2d');

    const resetButton = document.getElementById('resetButton');
    const menuDropdown = document.getElementById('menuDropdown');
    const timerDisplay = document.getElementById('timer');
  
    console.log('Script loaded');
    let dots = [];
    let startTime;
    let gameInterval;
    let selectedDot = null; // This will reference the currently selected dot if needed
    let dragOrigin = null;
    let lastRedKingdomSize = 0;
    let redKingdomDots = [];
  
    function adjustCanvasSize() {
        const rect = gameContainer.getBoundingClientRect();
        gameCanvas.width = rect.width;
        gameCanvas.height = rect.height;
        backgroundCanvas.width = rect.width;
        backgroundCanvas.height = rect.height;
    }
  
    window.addEventListener('resize', adjustCanvasSize);
    adjustCanvasSize();

    // Update timer
    function updateTimer() {
        const now = new Date();
        const elapsed = new Date(now - startTime);
        const minutes = elapsed.getUTCMinutes().toString().padStart(2, '0');
        const seconds = elapsed.getSeconds().toString().padStart(2, '0');
        timerDisplay.textContent = `${minutes}:${seconds}`;
    }

    // Start game call
    function startGame() {
        clearInterval(gameInterval);
        scatterDots();
        startTime = new Date();
        gameInterval = setInterval(() => {
            updateTimer();
            appreciateDots();

            const redKingdomDots = dots.filter(dot => dot.isRed);
            if (redKingdomDots.length !== lastRedKingdomSize) {

                // Clear the canvas at the start of each frame to ensure clean drawing
                bCtx.clearRect(0, 0, gameCanvas.width, gameCanvas.height);

                // Redraw the kingdom, ensuring it's behind everything else
                const redKingdomCoords = redKingdomDots.map(dot => ({ x: dot.x, y: dot.y }));
                const redKingdomCoordsAugmented = augmentCoords(redKingdomCoords);
        
                drawKingdom(redKingdomCoordsAugmented);

                lastRedKingdomSize = redKingdomDots.length;
            }

        }, 1000);
        console.log('Game started');
    }

    // 2. Game logic (Game API)

    // Appreciate dots
    function appreciateDots() {
        // console.log('Appreciating dots');
        dots.forEach(dot => {
            if (dot.count < (dot.isRed ? 20 : 10)) {
                dot.count++;
                dot.counter.textContent = dot.count;
            }
        });
    }

    // Scatter dots
    function scatterDots() {
        gameContainer.innerHTML = '';
        dots = [];
        let positions = generatePositions(50, 20);

        positions.forEach((pos, index) => {

            const dot = document.createElement('div');
            const counter = document.createElement('div');
            dot.className = 'dot';
            dot.style.left = `${pos.x}px`;
            dot.style.top = `${pos.y}px`;
            dot.isRed = index === 0;
            dot.style.backgroundColor = dot.isRed ? 'red' : 'black';
            dot.count = dot.isRed ? 0 : 0; // Initial soldier count for the dot
            
            counter.className = 'counter';
            // counter.textContent = dot.value;
            counter.textContent = dot.count;
            dot.appendChild(counter);

            gameContainer.appendChild(dot);

            // dots.push({ dot, counter, value: 1, isRed: dot.isRed, x: pos.x, y: pos.y });
            dots.push({ 
                dot, 
                counter, 
                // value: 1, 
                count: dot.count,
                isRed: dot.isRed, 
                x: pos.x, 
                y: pos.y,
                index: index // Add the dot's index here for easy reference
            });
            // Attach index to dot element for easy access
            dot.setAttribute('data-index', index);

            // Add event listener for dot click
            dot.addEventListener('mousedown', (e) => {
                e.preventDefault(); // Prevent text selection
                dragOrigin = { x: e.clientX - gameContainer.getBoundingClientRect().left, y: e.clientY - gameContainer.getBoundingClientRect().top, dot: dot };
                console.log(`Dragging ${dot.getAttribute('data-index')} (${dragOrigin.x}, ${dragOrigin.y})`);
                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
        });
    }
    function generatePositions(count, margin) {
        let positions = [];
        for (let i = 0; i < count; i++) {
            let position = {};
            do {
                position = {
                    x: Math.random() * (gameContainer.offsetWidth - margin * 4) + margin,
                    y: Math.random() * (gameContainer.offsetHeight - margin * 4) + margin
                };
            } while (positions.some(pos => 
                Math.sqrt((pos.x - position.x) ** 2 + (pos.y - position.y) ** 2) < margin
            ));
            positions.push(position);
        }
        return positions;
    }

    // 3. Gameplay for human players    

    gameContainer.addEventListener('mousemove', (e) => {
        const mouseX = e.clientX - gameContainer.getBoundingClientRect().left;
        const mouseY = e.clientY - gameContainer.getBoundingClientRect().top;

        // Apply hover effect to dots based on mouse position
        dots.forEach(dot => {
            const dx = mouseX - (dot.x + 5); // Adjusting for the visual offset
            const dy = mouseY - (dot.y + 5);
            const distance = Math.sqrt(dx * dx + dy * dy);
            if (distance < 20) { // Constant hover effect threshold
                dot.dot.style.border = "2px solid grey";
                dot.dot.style.left = `${dot.x - 2}px`; // Shift the dot to the left
                dot.dot.style.top = `${dot.y - 2}px`; // Shift the dot up       
                dot.hovered = true; // Set the hover flag to true
 
            } else {
                dot.dot.style.border = "";
                if (dot.hovered) { // If the dot was previously hovered over
                    dot.dot.style.left = `${dot.x}px`; // Reset the left position
                    dot.dot.style.top = `${dot.y}px`; // Reset the top position
                    dot.hovered = false; // Set the hover flag to false
                }        
            }
        });
    });

    // Clicking logic and arrows
    function onMouseMove(e) {
        if (!dragOrigin) return;
        const mouseX = e.clientX - gameContainer.getBoundingClientRect().left;
        const mouseY = e.clientY - gameContainer.getBoundingClientRect().top;
        let closestDot = null;
        let minDist = Infinity;

        console.log("Mouse move function called")

        // Check for hover effect and snap logic
        dots.forEach(dot => {
            const dx = mouseX - dot.x;
            const dy = mouseY - dot.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            if (distance < minDist && distance < 20) { // Snap threshold
                minDist = distance;
                closestDot = dot;
            }
        });

        // If close enough to a dot, snap the arrow to it
        if (closestDot) {
            drawArrow(dragOrigin.x, dragOrigin.y, closestDot.x + 5, closestDot.y + 5);
        } else {
            drawArrow(dragOrigin.x, dragOrigin.y, mouseX, mouseY);
        }
    }
    function drawArrow(fromX, fromY, toX, toY) {
        ctx.clearRect(0, 0, gameCanvas.width, gameCanvas.height); // Clear previous drawings
        const angle = Math.atan2(toY - fromY, toX - fromX);
        const headLength = 8;
        ctx.beginPath();
        ctx.moveTo(fromX, fromY);
        ctx.lineTo(toX, toY);
        ctx.lineTo(toX - headLength * Math.cos(angle - Math.PI / 6), toY - headLength * Math.sin(angle - Math.PI / 6));
        ctx.moveTo(toX, toY);
        ctx.lineTo(toX - headLength * Math.cos(angle + Math.PI / 6), toY - headLength * Math.sin(angle + Math.PI / 6));
        // ctx.strokeStyle = '#000';
        // Should be slightly transparent and the same colour 
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.9)';
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.closePath();
    }    

    // Roaming
    function onMouseUp(e) {
        if (!dragOrigin) return;
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);

        const mouseX = e.clientX - gameContainer.getBoundingClientRect().left;
        const mouseY = e.clientY - gameContainer.getBoundingClientRect().top;
        
        let closestDot = null; // Define closestDot within onMouseUp scope
        let minDist = Infinity;

        // Find if mouseup is over a dot (replicating logic from onMouseMove for closest dot)
        dots.forEach(dot => {
            const dx = mouseX - dot.x;
            const dy = mouseY - dot.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance < minDist) {
                minDist = distance;
                closestDot = dot;
            }
        });
        
        if (closestDot && minDist < 20) { // Ensure closest dot is within 20 pixels
            console.log(`Connected ${dragOrigin.dot.getAttribute('data-index')} (${dragOrigin.x}, ${dragOrigin.y}) to ${closestDot.index} (${closestDot.x}, ${closestDot.y})`);
            closestDot.dot.style.boxShadow = "0 0 10px #000";
            setTimeout(() => closestDot.dot.style.boxShadow = "", 2000);
            
            // Spawn and move soldiers
            spawnAndMoveSoldiers(dragOrigin.x, dragOrigin.y, closestDot.x + 5, closestDot.y + 5, parseInt(dragOrigin.dot.getAttribute('data-index')), closestDot.index); // Spawn 10 soldiers
        }

        dragOrigin = null;
    }

    function spawnAndMoveSoldiers(fromX, fromY, toX, toY, attackingDotIndex, targetDotIndex) {

        console.log(`Spawning soldiers from ${attackingDotIndex} to ${targetDotIndex}`);
        armySize = 8; // Number of soldiers to send

        const attackingDot = dots.find(dot => dot.index === attackingDotIndex);
    
        let soldiers = [];
        const speed = 0.5; // Speed of soldiers
        const repulsionRadius = 10; // Radius for repulsion effect among soldiers
        const repulsionStrength = 0.05; // Strength of the repulsion
    
        for (let i = 0; i < attackingDot.count; i++) {
            setTimeout(() => { // Stagger the creation and movement of soldiers
                const angle = Math.atan2(toY - fromY, toX - fromX);
                const soldier = {
                    x: fromX,
                    y: fromY,
                    dx: Math.cos(angle) * speed,
                    dy: Math.sin(angle) * speed,
                    active: true,
                    reached: false
                };
                soldiers.push(soldier);
    
                // Decrement count on the attacking dot for each soldier
                attackingDot.count -= 1;
                attackingDot.counter.textContent = attackingDot.count;

            }, i * 200); // Delay between each soldier's departure
        }
        
        let moveInterval = setInterval(() => {
            ctx.clearRect(0, 0, gameCanvas.width, gameCanvas.height); // Clear the canvas
    
            for (let i = 0; i < soldiers.length; i++) {
                const soldier = soldiers[i];
                if (!soldier.reached) {
                    // Repulsion logic among soldiers
                    for (let j = 0; j < soldiers.length; j++) {
                        if (i !== j) {
                            const other = soldiers[j];
                            let dx = soldier.x - other.x;
                            let dy = soldier.y - other.y;
                            let distance = Math.sqrt(dx * dx + dy * dy);
                            if (distance < repulsionRadius) {
                                dx /= distance;
                                dy /= distance;
                                soldier.x += dx * repulsionStrength;
                                soldier.y += dy * repulsionStrength;
                            }
                        }
                    }
    
                    // Movement towards the target
                    soldier.x += soldier.dx;
                    soldier.y += soldier.dy;
    
                    // Draw soldier
                    ctx.beginPath();
                    ctx.arc(soldier.x, soldier.y, 2, 0, Math.PI * 2);
                    ctx.fillStyle = 'blue';
                    ctx.fill();
    
                    // Check if the soldier has reached the target
                    if (Math.sqrt(Math.pow(soldier.x - toX, 2) + Math.pow(soldier.y - toY, 2)) < 5) {
                        soldier.reached = true;
                        // Update the target dot based on the soldier's impact
                        const targetDot = dots.find(dot => dot.index === targetDotIndex);
                        if (!targetDot.isRed) {
                            targetDot.count -= 1;
                            if (targetDot.count <= 0) {
                                targetDot.isRed = true;
                                targetDot.dot.style.backgroundColor = 'red';
                                targetDot.count = Math.abs(targetDot.count);
                            }
                        } else {
                            targetDot.count += 1;
                        }
                        targetDot.counter.textContent = targetDot.count;
                    }
                }
            }
    
            // Filter out soldiers that have reached the target
            soldiers = soldiers.filter(soldier => !soldier.reached);
    
            if (soldiers.length === 0) {
                clearInterval(moveInterval);
            }
        }, 20);
    }

    function augmentCoords(coords) {
        let augmentedPoints = [];

        coords.forEach(point => {
            // Add the original point to augmentedPoints
            augmentedPoints.push({x: point.x, y: point.y});
    
            // Generate 12 points around each original point
            for (let i = 0; i < 12; i++) {
                const angle = 2 * Math.PI * i / 12; // Divide the circle into 12 segments
                const offsetX = Math.cos(angle) * 15; // 20 is the radius around the point
                const offsetY = Math.sin(angle) * 15;
                augmentedPoints.push({x: point.x + 5 + offsetX, y: point.y + 5 + offsetY});
            }
        });
    
        return augmentedPoints;
    }

    function drawKingdom(coords) {
        length_of_coords = coords.length;
        for (let i = 0; i < coords.length; i++) {
            // console.log("Coords:", coords[i]);
            length_of_coords += 1;
        }
        // console.log("Length of coords:", length_of_coords);
        const points = coords.map(coord => ({ x: coord.x, y: coord.y }));

        // Compute the convex hull of the points
        const convexHullPoints = convexHull(points);
    


        bCtx.beginPath();
        bCtx.moveTo(convexHullPoints[0].x, convexHullPoints[0].y);
        for (let i = 1; i < convexHullPoints.length; i++) {
            bCtx.lineTo(convexHullPoints[i].x, convexHullPoints[i].y);
        }
        bCtx.closePath();
    
        bCtx.fillStyle = 'lightcoral';
        bCtx.fill();

    }

    function orientation(p, q, r) {
        const val = (q.y - p.y) * (r.x - q.x) - (q.x - p.x) * (r.y - q.y);
        if (val == 0) return 0; // Collinear
        return (val > 0) ? 1 : 2; // Clockwise or counterclockwise
    }

    function convexHull(points) {
        if (points.length < 3) return points; // Convex hull not possible with less than 3 points
        
        // Find the pivot point (point with lowest y-coordinate, and leftmost in case of a tie)
        let pivot = points[0];
        for (let i = 1; i < points.length; i++) {
            if (points[i].y < pivot.y || (points[i].y === pivot.y && points[i].x < pivot.x)) {
                pivot = points[i];
            }
        }
        
        // Sort the points by the angle they make with the pivot point in counterclockwise order
        const sortedPoints = points.slice().sort((a, b) => {
            const orientationVal = orientation(pivot, a, b);
            if (orientationVal === 0) {
                // If collinear, choose the point closest to the pivot
                return ((a.x - pivot.x) ** 2 + (a.y - pivot.y) ** 2) - ((b.x - pivot.x) ** 2 + (b.y - pivot.y) ** 2);
            }
            return (orientationVal === 2) ? -1 : 1; // Sort by counterclockwise angle
        });
        
        // Initialize an empty stack and push pivot and the first point from the sorted list onto the stack
        const stack = [pivot, sortedPoints[0]];
        
        // Iterate through the sorted list of points
        for (let i = 1; i < sortedPoints.length; i++) {
            while (stack.length > 1 && orientation(stack[stack.length - 2], stack[stack.length - 1], sortedPoints[i]) !== 2) {
                stack.pop(); // Pop points that make a right turn or are collinear with the top two points on the stack
            }
            stack.push(sortedPoints[i]); // Push the current point onto the stack
        }
        
        return stack; // Stack now contains the convex hull points
    }

    





    menuDropdown.addEventListener('change', (e) => {
        if (e.target.value === 'restart') {
        startGame();
        e.target.value = 'start'; // Resetting the dropdown
        }
    });

    

    startGame(); // Automatically start the game when the page loads
});