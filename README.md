# MRI image data pipeline exercise

* How did you verify that you are parsing the contours correctly?

  * I used a Jupyter notebook to load DICOM images and contours and display them.
    I displayed the contour masks overlaid on the DICOM images and manually
    verified a few sets.

* What changes did you make to the functions that we provided, if any, in order to
integrate them into a production code base?

  * I made the `parse_dicom_file` function just return the actual image instead
    of a dictionary. I can see how it might be useful in the future, but it
    made the parsing APIs inconsistent and it would be easy to add later if
    needed
  * I added error handling in the `parse_contour_file` and `poly_to_mask`
    functions. If any of the parsing functions fail we want to continue
    processing images, so we need to catch exceptions here.

* If the pipeline was going to be run on millions of images, and speed was
paramount, how would you parallelize it to run as fast as possible?

  * I would have one thread writing images to be loaded into a queue, and worker
    threads taking jobs off of the queue to load from disk. You could also
    divide up the work to be done at the start, and have each thread be
    responsible for loading a subset of the data.

* If this pipeline were parallelized, what kinds of error checking and/or
safeguards, if any, would you add into the pipeline?

  * You would need to make sure that only one thread tries to load any given
    image.
  * You would want your loading process to be robust to crashes in any single
    thread.


* How did you choose to load each batch of data asynchronously, and why did you
choose that method? Were there other methods that you considered - what are the
pros/cons of each?

  * I chose to load the data in a single separate process with
    `multiprocessing`. I chose this method on the assumption that each training
    step would take longer than loading a batch of data, so the producer should
    always be able to stay ahead of the consumer. I also chose it because it's
    less complex and hopefully less error-prone. If this assumption didn't hold,
    I would probably implement it as a pool of workers with
    `multiprocessing.Pool` in order to speed up the loading. The producer is
    constrained to not get too far ahead of the consumer (which would use more
    memory than necessary) by giving the Queue a maxsize of 2.

* What kinds of error checking and/or safeguards, if any, did you build into this
part of the pipeline to prevent the pipeline from crashing when run on thousands
of studies?

  * The `data_load_worker` wraps each successive load attempt in a try/catch
    that would prevent the whole process from failing. The actual loading
    functions try to catch errors and generally just return `None` as a signal
    to skip the current element.

* Did you change anything from the pipelines built in Parts 1 to better streamline
the pipeline built in this part? If so, what? If not, is there anything that you
can imagine changing in the future?

  * Yes, I separated the logic for enumerating the data files from the logic of
    loading them because of the constraint that we need to pull randomly from
    the entire dataset. My previous version would have only allowed us to pull
    randomly from within one study at a time.

* How did you verify that the pipeline was working correctly?

  * I parameterized the `data_load_worker` to take a `loader_fn` that can
    optionally be swapped with a stub implementation (with `TEST=true python
    pipeline.py`). The stub implementation just uses the filenames as the data
    to load so it can be easily verified in the terminal. The actual loading (as
    mentioned above) was verified with a Jupyter notebook. If I had more time to
    work on this I would integrate the tests with an actual unit testing
    framework (I'm partial to [pytest](https://docs.pytest.org/en/latest/)).

* Given the pipeline you have built, can you see any deficiencies that you would
change if you had more time? If not, can you think of any
improvements/enhancements to the pipeline that you could build in?

  * The current implementation is fairly rigid on the format of the filenames
    and directory structure. I would make that more configurable so it could be
    reused with other datasets.
  * With more time, I would probably experiment with different methods of doing
    the parallel loading, like the `multiprocessing.Pool` method suggested
    above.

