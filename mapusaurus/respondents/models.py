from django.db import models
from django.template import defaultfilters
from localflavor.us.models import USStateField
import json
from respondents.managers import AgencyManager

class ZipcodeCityState(models.Model):
    """ For each zipcode, maintain the city, state information. """
    zip_code = models.IntegerField()
    plus_four = models.IntegerField(null=True)
    city = models.CharField(max_length=25)
    state = USStateField()

    class Meta:
        unique_together = ('zip_code', 'city')

    @property
    def unique_name(self):
        return '%s, %s %s' % (self.city, self.state, self.zip_code)

    def __unicode__(self):
        return self.unique_name


class Agency(models.Model):
    """ Agencies of the government that are referenced in the HMDA dataset. """

    hmda_id = models.IntegerField(primary_key=True)
    acronym = models.CharField(max_length=10)
    full_name = models.CharField(max_length=50)

    objects = AgencyManager()

    def __unicode__(self):
        return self.acronym


class ParentInstitution(models.Model):
    """ Parent and top holder institutions need to be stored a bit differently
    because (1) they can be international and (2) they might not report HMDA so
    we have fewer details. If we have an RSSD ID we try and store it here. """

    year = models.SmallIntegerField()
    name = models.CharField(max_length=30)
    city = models.CharField(max_length=25)
    state = models.CharField(max_length=2, null=True)
    country = models.CharField(max_length=40, null=True)
    rssd_id = models.CharField(
        max_length=10,
        unique=True,
        help_text='Id on the National Information Center repository',
        null=True)

    def __unicode__(self):
        return self.name


class Institution(models.Model):
    """ An institution's (aka respondent) details. These can change per year.
    """

    year = models.SmallIntegerField()
    respondent_id = models.CharField(max_length=10)
    agency = models.ForeignKey('Agency')
    institution_id = models.CharField(max_length=11, primary_key=True)
    tax_id = models.CharField(max_length=10)
    name = models.CharField(max_length=30)
    mailing_address = models.CharField(max_length=40)
    zip_code = models.ForeignKey('ZipCodeCityState', null=False)
    assets = models.PositiveIntegerField(
        default=0,
        help_text='Prior year reported assets in thousands of dollars'
    )
    rssd_id = models.CharField(
        max_length=10,
        null=True,
        help_text='From Reporter Panel. Id on the National Information Center repository')
    parent = models.ForeignKey(
        'self',
        null=True,
        related_name='children',
        help_text='The parent institution')
    non_reporting_parent = models.ForeignKey(
        'ParentInstitution',
        null=True,
        related_name='children',
        help_text='Non-HMDA reporting parent')
    top_holder = models.ForeignKey(
        'ParentInstitution',
        related_name='descendants',
        null=True,
        help_text='The company at the top of the ownership chain.')

    def formatted_name(self):
        formatted = defaultfilters.title(self.name) + " ("
        formatted += str(self.agency_id) + self.respondent_id + ")"
        return formatted

    class Meta:
        unique_together = ('institution_id', 'year')
        index_together = [['institution_id', 'year']]

    def __unicode__(self):
        return self.name

class LenderHierarchy(models.Model):
    institution = models.ForeignKey('Institution', to_field='institution_id')
    organization_id = models.IntegerField()

class Branch(models.Model):
    year = models.SmallIntegerField()
    institution = models.ForeignKey('Institution', to_field='institution_id')
    name = models.CharField(max_length=50)
    street = models.CharField(max_length=100)
    city = models.CharField(max_length=25)
    state = USStateField()
    zipcode = models.IntegerField()
    lat = models.FloatField(help_text='y')
    lon = models.FloatField(help_text='x')

    def branch_as_geojson(self):
        """Convert this model into a geojson string"""
        geojson = {'type': 'Feature',
                   'properties': {
                       'year': self.year,
                       'institution_id': self.institution_id,
                       'name': self.name,
                       'street': self.street,
                       'city': self.city,
                       'state': self.state,
                       'zipcode': self.zipcode,
                       'lat': self.lat,
                       'lon': self.lon}}
        geojson = json.dumps(geojson)
        return geojson
