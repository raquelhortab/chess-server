from flask_wtf import FlaskForm

from wtforms import StringField, SubmitField
from wtforms.validators import Length


class GameForm(FlaskForm):
    pc_id = StringField('Pc ID')
    handle = StringField('Karel handle choosed by the user', validators=[Length(4, 64)])
    submit = SubmitField('Submit')

