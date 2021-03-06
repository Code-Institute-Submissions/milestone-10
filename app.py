import os
import random
import datetime
import bcrypt
from flask import Flask, render_template, redirect, request, url_for, session, abort
from flask_pymongo import PyMongo
from bson.objectid import ObjectId

APP = Flask(__name__)

APP.config["SECRET_KEY"] = os.environ.get('SECRET_KEY')
APP.config["MONGO_DBNAME"] = os.environ.get('MONGO_DBNAME')
APP.config["MONGO_URI"] = os.environ.get('MONGO_URI')

MONGO = PyMongo(APP)

@APP.errorhandler(404)
def page_not_found(e):
    """
    Returns page not found message on error page.
    """
    return render_template('pages/error.html', headerTitle="Error - Page Not Found", message=e), 404

@APP.errorhandler(401)
def not_authorized(e):
    """
    Returns unathorized message on error page.
    """
    return render_template('pages/error.html', headerTitle="Error - Not Authorized", message=e), 401

@APP.route('/')
def home():
    """
    Renders homepage, and generates all drinks in db.
    Sorts in reverse order by key modifiedDate.
    """
    today = datetime.datetime.now()
    sorted_drinks = MONGO.db.drinks.find().sort('modifiedDate', -1)
    return render_template('pages/home.html',
                           drinks=sorted_drinks,
                           headerTitle="Latest Drinks",
                           ingredients=MONGO.db.ingedients.find())


@APP.route('/logout')
def logout():
    """
    Checks if user is logged in. Prevents non-logged in users accessing logout function.
    If user is logged in, terminate session.
    If no user logged in, sent to home page.
    """
    if 'username' in session:
        session.pop('username')
    return redirect(url_for('home'))

#Below definition is taken and tailored from PrettyPrinted. Please refer to Credits section of README.md for more info.
@APP.route('/login', methods=['POST', 'GET'])
def login():
    """
    Cross references supplied login info with DB.
    If correct, sets session to username.
    If failure, returns login page with error.
    """
    if request.method == 'POST':
        form = request.form.to_dict()
        users = MONGO.db.users
        login_user = users.find_one({'username': form['username']})
        if login_user:
            if bcrypt.hashpw(form['password'].encode('utf-8'),
                             login_user['password']) == login_user['password']:
                session['username'] = form['username']
                return redirect(url_for('home'))
        return render_template('pages/login.html',
                               invalid=True)
    return render_template('pages/login.html')

#Below definition is taken and tailored from PrettyPrinted. Please refer to Credits section of README.md for more info.
@APP.route('/register', methods=['POST', 'GET'])
def register():
    """
    Checks is user already exists.
    Encrypts the supplied password using a generated salt.
    Pushes information in form to database.
    Logs in user, and returns to home.
    Failures return to register page with message.
    """
    if request.method == 'POST':
        form = request.form.to_dict()
        users = MONGO.db.users
        existing_user = users.find_one({'username': request.form['username']})
        if existing_user is None:
            hashpass = bcrypt.hashpw(
                form['password'].encode('utf-8'), bcrypt.gensalt())
            user_details = {
                'username': form["username"],
                'email': form["email"],
                'password': hashpass
            }
            users.insert_one(user_details)
            session['username'] = form['username']
            return redirect(url_for('home'))
        return render_template('pages/register.html',
                               exists=True,
                               headerTitle='Register')
    return render_template('pages/register.html',
                           headerTitle='Register')

@APP.route('/ingredients', methods=['GET', 'POST'], defaults={'ingredient_name': {}})
@APP.route('/ingredients/<ingredient_name>', methods=['GET', 'POST'])
def ingredients(ingredient_name):
    """
    Renders all ingredients within page.
    Retrieves all documents from ingredients database.
    """
    ingredients_list = MONGO.db.ingedients.find()
    drinks_list = MONGO.db.drinks.find()
    ingredient_dict = {
        'ingredientList': ingredient_name
    }
    if request.method == 'POST':
        ingredient_search = request.form.to_dict()
        if not ingredient_search:
            return render_template('pages/ingredients.html',
                                   ingredients=ingredients_list,
                                   ingredient=ingredient_search,
                                   headerTitle='No ingredient selected')
        return render_template('pages/ingredients.html',
                               ingredients=ingredients_list,
                               ingredient=ingredient_search,
                               drinks=drinks_list,
                               headerTitle=ingredient_search['ingredientList'])
    return render_template('pages/ingredients.html',
                           drinks=drinks_list,
                           ingredient=ingredient_dict,
                           ingredients=ingredients_list,
                           headerTitle="Ingredients")


@APP.route('/collection/<collectionType>')
@APP.route('/collection/', defaults={'collectionType':{}})
def collection(collectionType):
    """
    Renders page which display all drinks in drinks database.
    If username supplied, shows only drinks by that user.
    If my drinks argument supplied, returns users own drinks.
    On error, returns a user not found error page.
    """
    if collectionType == 'my-drinks':
        if 'username' in session:
            if session['username'] == 'admin':
                return render_template('pages/collection.html',
                                       drinks=MONGO.db.drinks.find(),
                                       ingredients=MONGO.db.ingedients.find(),
                                       headerTitle="My Drinks")
            drinkCount = MONGO.db.drinks.find({"createdBy": session['username']}).count()
            return render_template('pages/collection.html',
                                   drinkCount=drinkCount,
                                   drinks=MONGO.db.drinks.find({"createdBy": session['username']}),
                                   ingredients=MONGO.db.ingedients.find(),
                                   headerTitle="My Drinks")
        return redirect(url_for('login'))
    elif collectionType:
        userExists = MONGO.db.users.find_one({"username": collectionType})
        if userExists:
            drinkCount = MONGO.db.drinks.find({"createdBy": collectionType}).count()
            if not drinkCount:
                return abort(404, description="No collection found for this user!")
            return render_template('pages/collection.html',
                                   drinkCount=drinkCount,
                                   drinks=MONGO.db.drinks.find({"createdBy": collectionType}),
                                   ingredients=MONGO.db.ingedients.find(),
                                   headerTitle="My Drinks")
        return abort(404, "User not found!")
    return render_template('pages/collection.html',
                           drinks=MONGO.db.drinks.find(),
                           ingredients=MONGO.db.ingedients.find(),
                           headerTitle="Collection")

@APP.route('/add-ingredient', methods=['POST', 'GET'])
def add_ingredient():
    """
    Takes info from ingredient modal.
    Checks DB for record. If no record found, posts to DB.
    If record found, returns error with already existing.
    """
    if 'username' in session:
        if request.method == 'POST':
            ingredients_list = MONGO.db.ingedients
            today = datetime.datetime.now()
            form = request.form.to_dict()
            final_ingredient = {
                'ingredientName': form["ingredientName"].title(),
                'ingredientImage': form["ingredientImage"],
                'modifiedDate': str(today)
            }
            mongo_count = ingredients_list.find_one(
                {'ingredientName': form["ingredientName"]})
            if mongo_count is None:
                ingredients_list.insert_one(final_ingredient)
                return redirect(url_for('home'))
            return render_template('addingredient.html',
                                   exists=1,
                                   ingredient=final_ingredient,
                                   headerTitle="Add Ingredient")
        return render_template('addingredient.html',
                               headerTitle="Add Ingredient")
    return redirect(url_for('home'))


@APP.route('/drink/<drink_id>', methods=['POST', 'GET'])
def drink(drink_id):
    """
    Renders page for viewing all drink details for drink found in DB.
    On POST, checks DB from drink of the same name.
    On returning record, reroutes to drink page that already exists.
    When no record found, posts drink to DB, and redirects back to new page.
    With randomDrink argument, returns a random drink from database.
    """
    try:
        if request.method == 'POST':
            if drink_id == 'insertDrink':
                drinks = MONGO.db.drinks
                form = request.form.to_dict()
                today = datetime.datetime.now()
                exists = drinks.find_one({"drinkName": str(form["drinkName"].title())})
                if exists:
                    return render_template('pages/viewdrink.html',
                                           drink=exists,
                                           headerTitle=request.form.get('drinkName'),
                                           ingredients=MONGO.db.ingedients.find(),
                                           editIngredients=MONGO.db.ingedients.find(),
                                           exists=1)
                final_drink = {
                    'drinkName': form["drinkName"].title(),
                    'drinkImage': form["drinkImage"],
                    'ingredientList': request.form.getlist("ingredientName"),
                    'instructions': form["instructions"],
                    'modifiedDate': str(today),
                    'createdBy': session['username'],
                }
                insertedDrink = drinks.insert_one(final_drink).inserted_id
                the_drink=MONGO.db.drinks.find_one({"_id": ObjectId(insertedDrink)})
                return render_template('pages/viewdrink.html',
                                       drink=the_drink,
                                       headerTitle=request.form.get('drinkName'),
                                       ingredients=MONGO.db.ingedients.find(),
                                       editIngredients=MONGO.db.ingedients.find())
            drinks = MONGO.db.drinks
            today = datetime.datetime.now()
            drinks.update_one({'_id': ObjectId(drink_id)},
                              {'$set':
                               {
                                   'drinkImage': request.form.get('drinkImage'),
                                   'drinkName': request.form.get('drinkName'),
                                   'ingredientList': request.form.getlist("ingredientName"),
                                   'modifiedDate': str(today),
                                   'instructions': request.form.get('instructions')
                               }
                               },
                              upsert=False)
            return render_template('pages/viewdrink.html',
                                   drink=MONGO.db.drinks.find_one({"_id": ObjectId(drink_id)}),
                                   headerTitle=request.form.get('drinkName'),
                                   ingredients=MONGO.db.ingedients.find(),
                                   editIngredients=MONGO.db.ingedients.find())
        elif drink_id == 'randomDrink':
            rand = MONGO.db.drinks.count()
            the_drink = MONGO.db.drinks.find()[random.randrange(rand)]
            return render_template('pages/viewdrink.html',
                                   drink=the_drink,
                                   headerTitle=the_drink['drinkName'],
                                   ingredients=MONGO.db.ingedients.find(),
                                   editIngredients=MONGO.db.ingedients.find())
        else:
            the_drink = MONGO.db.drinks.find_one({"_id": ObjectId(drink_id)})
            return render_template('pages/viewdrink.html',
                                   drink=the_drink,
                                   headerTitle=the_drink['drinkName'],
                                   ingredients=MONGO.db.ingedients.find(),
                                   editIngredients=MONGO.db.ingedients.find())
    except:
        return abort(404, "Drink does not exist!")


@APP.route('/delete-drink/<drink_id>')
def delete_drink(drink_id):
    """
    Checks if delete request comes from drink creator.
    Deletes drink from collection once confirmed on page.
    Returns error if drink doesn't exists, or incorrect info provided in URL.
    """
    try:
        the_drink = MONGO.db.drinks.find_one({"_id": ObjectId(drink_id)})
        if 'username' in session:
            if session['username'] == the_drink['createdBy']:
                MONGO.db.drinks.delete_one({"_id": ObjectId(drink_id)})
                return redirect(url_for('collection', collectionType='my-drinks'))
            return abort(401, "Not authorized to delete this drink!")
        return abort(401, "Please login to delete drinks!")
    except:
        return abort(404, "Drink not found!")

if __name__ == '__main__':
    APP.run(host=os.environ.get('IP'),
            port=os.environ.get('PORT'),
            debug=False)
