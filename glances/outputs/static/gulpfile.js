var gulp = require('gulp');
var concat = require('gulp-concat');
var mainBowerFiles = require('main-bower-files');
var ngAnnotate = require('gulp-ng-annotate');
var templateCache = require('gulp-angular-templatecache');
var del = require('del');
var rename = require('gulp-rename');

gulp.task('clean', function() {
  del('./public/*')
});

gulp.task('copy', function() {
  gulp.src('./html/*.html')
    .pipe(gulp.dest('./public'));

  gulp.src('./css/*.css')
    .pipe(rename({suffix: '.min'}))
    .pipe(gulp.dest('./public/css'));

  gulp.src('./images/*.png')
    .pipe(gulp.dest('./public/images'));

  gulp.src('favicon.ico')
    .pipe(gulp.dest('./public'));
});

gulp.task('bower', function() {
  return gulp.src(mainBowerFiles())
    .pipe(concat('vendor.js'))
    .pipe(rename({suffix: '.min'}))
    .pipe(gulp.dest('./public/js'))
});

gulp.task('build-js', function() {
  return gulp.src('./js/**/*.js')
    .pipe(ngAnnotate())
    .pipe(concat('main.js'))
    .pipe(rename({suffix: '.min'}))
    .pipe(gulp.dest('./public/js'))
});

gulp.task('template', function () {
  return gulp.src('./html/plugins/*.html')
    .pipe(templateCache('templates.js', {'root': 'plugins/', 'module': 'glancesApp'}))
    .pipe(rename({suffix: '.min'}))
    .pipe(gulp.dest('./public/js'));
});

gulp.task('watch', function () {
  gulp.watch(['./html/*.html','./css/*.css', './images/*.png'], ['copy']);
  gulp.watch('bower.json', ['bower']);
  gulp.watch('./js/**/*.js', ['build-js']);
  gulp.watch('./html/plugins/*.html', ['template']);
});

gulp.task('build', ['clean', 'bower', 'build-js', 'template', 'copy']);
gulp.task('default', ['build']);
