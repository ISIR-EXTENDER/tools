#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int starts_with(const char * value, const char * prefix)
{
  return strncmp(value, prefix, strlen(prefix)) == 0;
}

static int is_snap_library_path(const char * path)
{
  return starts_with(path, "/snap/") || starts_with(path, "/var/lib/snapd/");
}

static void append_path(char * output, const char * path)
{
  if (output[0] != '\0') {
    strcat(output, ":");
  }
  strcat(output, path);
}

static void clean_ld_library_path(void)
{
  const char * value = getenv("LD_LIBRARY_PATH");
  if (value == NULL || value[0] == '\0') {
    return;
  }

  char * input = strdup(value);
  char * output = calloc(strlen(value) + 1, sizeof(char));
  if (input == NULL || output == NULL) {
    free(input);
    free(output);
    return;
  }

  char * cursor = input;
  while (cursor != NULL) {
    char * separator = strchr(cursor, ':');
    if (separator != NULL) {
      *separator = '\0';
    }

    if (cursor[0] != '\0' && !is_snap_library_path(cursor)) {
      append_path(output, cursor);
    }

    cursor = separator == NULL ? NULL : separator + 1;
  }

  if (output[0] == '\0') {
    unsetenv("LD_LIBRARY_PATH");
  } else {
    setenv("LD_LIBRARY_PATH", output, 1);
  }

  free(input);
  free(output);
}

int main(int argc, char ** argv)
{
  const char * python = "/usr/bin/python3";
  const char * module = "signal_processing.signal_processing_tester";
  const int forwarded_argc = argc > 1 ? argc - 1 : 0;
  char ** python_argv = calloc((size_t)forwarded_argc + 4, sizeof(char *));
  if (python_argv == NULL) {
    fprintf(stderr, "signal_processing_tester: failed to allocate launcher arguments\n");
    return 127;
  }

  clean_ld_library_path();

  python_argv[0] = (char *)python;
  python_argv[1] = "-m";
  python_argv[2] = (char *)module;
  for (int index = 0; index < forwarded_argc; ++index) {
    python_argv[index + 3] = argv[index + 1];
  }
  python_argv[forwarded_argc + 3] = NULL;

  execv(python, python_argv);
  perror("signal_processing_tester: failed to execute /usr/bin/python3");
  free(python_argv);
  return 127;
}
