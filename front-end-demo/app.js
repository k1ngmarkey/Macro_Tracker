/* Program handling user inputs on web page for macronutrient tracking.
 * Made by: Easton Walsh and Tyson Terrington
 * Date created: 2026-11-09
 * Last modified: 2026-11-24
 */

//Interface items
const add_btn = document.getElementById('addBtn');
//const view_btn = document.getElementById('viewBtn');
const recipe_btn = document.getElementById('recipeBtn');
const home_btn = document.getElementById('homeBtn');
const recipe_page = document.getElementById('recipe-page');
const home_page = document.getElementById('home-page');
const view_page = document.getElementById('view-page');
const add_page = document.getElementById('add-page');

// Hard coded values, should connect to back end for proper use
goals = {
    cal: 2200,
    p: 160,
    c: 240,
    f: 70
}

//Hiding all but home page
home_page.hidden = false;
recipe_page.hidden = true;
//view_page.hidden = true; //not implemented
add_page.hidden = true;

//Set active page
current_page = home_page;

//Open the add page
add_btn.addEventListener('click', () => {
    current_page.hidden = true;
    add_page.hidden = false;
    current_page = add_page;
});

/*Open the view page | Feature not implemented
view_btn.addEventListener('click', () => {
    current_page.hidden = true;
    view_page.hidden = false;
    current_page = view_page;
});*/

//Open the recipe page
recipe_btn.addEventListener('click', () => {
    current_page.hidden = true;
    recipe_page.hidden = false;
    current_page = recipe_page;
});


//Open the add page
home_btn.addEventListener('click', () => {
    current_page.hidden = true;
    home_page.hidden = false;
    current_page = home_page;
    displayHome();
    testDays[0] = {date: 'Wednesday, Nov 25 2026', p: p, f: f, c: c, cal: cals}
    listDays(testDays, 7, dayText);
    

});

//Home Page
const calsTotal = document.getElementById('home-cals');
const carb_bar = document.getElementById('home-c');
const fat_bar = document.getElementById('home-f');
const protein_bar = document.getElementById('home-p');

//Hard coded values, back end never done
//Back end not connected
cals = 1000; 
c = 220;
p = 25;
f = 45;

//Function to dipslay progress bars as combinations of dots and hashtags between square brackets
function barProgressDisplay(max, val){
    count = Math.floor((val/max) * 20);
    if(count > 20){
        count = 20;
    }
    return '[' + '#'.repeat(count) + '.'.repeat(3*(20 - count)) + '] '
}
function displayHome(){
    calsTotal.textContent = 'CAL ' + barProgressDisplay(goals.cal, cals) + cals + '/' + goals.cal;
    protein_bar.textContent = 'PRO ' + barProgressDisplay(goals.p, p) + p + '/' + goals.p;
    fat_bar.textContent = 'FAT ' + barProgressDisplay(goals.f, f) + f + '/' + goals.f;
    carb_bar.textContent = 'CARB ' + barProgressDisplay(goals.c, c) + c + '/' + goals.c;
}
displayHome()
//import the saved days here

dayText = [];
function days(){
    for(let i = 1; i < 8; i++){
        day = {
            date: document.getElementById("day" + i),
            cal: document.getElementById("day" + i + '-cal'),
            mac: document.getElementById("day" + i + '-mac'),
        }
        dayText.push(day);
    }
}

days();

function listDays(days, n, textboxes){
    
    //Assumed to take a list of days, each day being an object
    for(let i = 0; i < n; i++){
        infoDay = days[i];
        
        textboxes[i].date.textContent = infoDay.date;
        if(i == 0){
            textboxes[i].date.textContent += ' (today)';
        }
        textboxes[i].cal.textContent = infoDay.cal + 'cal';
        textboxes[i].mac.textContent = infoDay.p + 'p' + '\n' + infoDay.f + 'f' +  '\n' + infoDay.c + 'c';
    }

}
testDays = [{date: 'Wednesday, Nov 25 2026', p: p, f: f, c: c, cal: cals}, {date: 'Tuesday, Nov 24 2026', p: 100, f: 50, c: 200, cal: 2000}, {date: 'Monday, Nov 23 2026', p: 100, f: 50, c: 200, cal:2000}, {date: 'Sunday, Nov 22 2026', p: 100, f: 50, c: 200, cal:2000}, {date: 'Saturday, Nov 21 2026', p: 100, f: 50, c: 200, cal:2000}, {date: 'Friday, Nov 20 2026', p: 100, f: 50, c: 200, cal:2000}, {date: 'Thursday, Nov 19 2026', p: 100, f: 50, c: 200, cal:2000}, {date: 'Wednesday, Nov 18 2026', p: 100, f: 50, c: 200, cal:2000}];

listDays(testDays, 7, dayText);

//View days

//Planned, but not implemented

//Track a meal

const search_txt = document.getElementById('search-input');
const search_btn = document.getElementById('search-btn');
const results = document.getElementById("item-list");

search_btn.addEventListener('click', () => {
    item = search_txt.value;
    search_txt.value = '';

    //Call the backend to search through all the items with this string and return them as a list/array
    list = ['Chicken', 'Fried chicken', 'Grilled Chicken'];
    renderList(list);
});

function renderList(items){
    results.innerHTML = ""; // Clear existing list before re-rendering

    items.forEach((item, index) => {
    const li = document.createElement("li");

    const span = document.createElement("span");
    span.textContent = item + " ";

    const btn = document.createElement("button");
    btn.textContent = "Add"; // Or "Select", "Edit", etc.
    btn.classList.add("small-btn");
    btn.addEventListener('click', () => {
        results.innerHTML = "";
        cals += 100; //These values would be brought from the back end
        p += 20;
        f += 4;
        c += 0;
    })
    btn.dataset.index = index;  // Store the item's position on the button

    li.appendChild(span);
    li.appendChild(btn);
    results.appendChild(li);
    });
}
//New Recipe

const addRecipe_btn = document.getElementById('add-recipe');
const cal_txt = document.getElementById('cal-input');
const pro_txt = document.getElementById('pro-input');
const carb_txt = document.getElementById('carb-input');
const fat_txt = document.getElementById('fat-input');
const name_txt = document.getElementById('name-input');

//Adds the recipe to list of possible meals. Not connected to back end so doesnt actually do anything
addRecipe_btn.addEventListener('click', () => {
    recipeName = name_txt.value;
    cals = parseFloat(cal_txt.value);
    protein = parseFloat(pro_txt.value);
    carb = parseFloat(carb_txt.value);
    fat = parseFloat(fat_txt.value);
    if(cals >= 0 && protein >= 0 && carb >= 0 && fat >= 0 && typeof recipeName === "string" && recipeName.trim().length > 0){
        //Send to back end, no idea where so just use your imagination
        console.log([recipeName, cals, protein, carb, fat]); //Just to have as an example
        name_txt.value = '';
        cal_txt.value = '';
        carb_txt.value = '';
        pro_txt.value = '';
        fat_txt.value = '';
    } else{
        alert('At least one input is invalid or empty');
    }

});
